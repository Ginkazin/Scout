"""Integração HTTP de Server: JWT, PostgreSQL, ownership e regras de assinatura."""

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.core.security import DUMMY_PASSWORD_HASH, create_access_token
from app.models.agent import Agent
from app.models.alert import Alert, AlertSeverity
from app.models.customer import Customer
from app.models.metric import Metric
from app.models.server import Server, ServerType
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User, UserRole


@pytest_asyncio.fixture
async def owner_factory(db_session, free_plan):
    async def create(status=SubscriptionStatus.ACTIVE):
        user = User(name="Server Teste", email=f"{uuid4().hex}@example.com",
                    password_hash=DUMMY_PASSWORD_HASH, role=UserRole.ADMIN)
        db_session.add(user)
        await db_session.flush()
        db_session.add(Subscription(user_id=user.id, plan_id=free_plan.id, status=status))
        await db_session.flush()
        return user, {"Authorization": f"Bearer {create_access_token(user.id)}"}
    return create


@pytest_asyncio.fixture
async def customer_factory(db_session):
    async def create(user):
        customer = Customer(user_id=user.id, name=f"Empresa {uuid4().hex}")
        db_session.add(customer)
        await db_session.flush()
        return customer
    return create


@pytest_asyncio.fixture
async def server_factory(db_session):
    async def create(customer, **fields):
        server = Server(customer_id=customer.id, **{"name": "Servidor ERP", "os_family": "LINUX", **fields})
        db_session.add(server)
        await db_session.flush()
        return server
    return create


@pytest_asyncio.fixture
async def owner(owner_factory):
    return await owner_factory()


@pytest_asyncio.fixture
async def customer(owner, customer_factory):
    return await customer_factory(owner[0])


def collection(customer):
    return f"/customers/{customer.id}/servers"


async def count_servers(db_session, customer):
    return await db_session.scalar(
        select(func.count()).select_from(Server).where(Server.customer_id == customer.id)
    )


@pytest.mark.parametrize("ip", ["192.0.2.10", "2001:db8::10"], ids=["ipv4", "ipv6"])
async def test_create_server_persists_fields(client, db_session, owner, customer, ip):
    payload = dict(os_family="LINUX", name="Servidor ERP", server_type="DEDICATED", hostname="erp.example.com",
                   ip_address=ip, operating_system="Linux", description="Servidor principal")
    response = await client.post(collection(customer), headers=owner[1], json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["customer_id"] == str(customer.id)
    assert body["is_active"] is True
    assert body["created_at"] and body["updated_at"]
    server = await db_session.get(Server, UUID(body["id"]))
    assert server.customer_id == customer.id
    for field, value in payload.items():
        assert body[field] == value
        assert getattr(server, field) == value


@pytest.mark.parametrize("os_family,description", [
    ("LINUX", "Ubuntu 24.04"), ("WINDOWS", "Windows Server 2022"),
])
async def test_server_os_family_persists_separately_from_description(
    client, db_session, owner, customer, os_family, description
):
    response = await client.post(
        collection(customer), headers=owner[1],
        json={"name": "Servidor SO", "os_family": os_family, "operating_system": description},
    )
    assert response.status_code == 201, response.text
    server_id = UUID(response.json()["id"])
    server = await db_session.get(Server, server_id)
    assert server.os_family == os_family
    assert server.operating_system == description
    fetched = await client.get(f"/servers/{server_id}", headers=owner[1])
    assert fetched.status_code == 200
    assert fetched.json()["os_family"] == os_family
    assert fetched.json()["operating_system"] == description
    # Alterar a descrição não apaga ou redefine a família do SO.
    patched = await client.patch(
        f"/servers/{server_id}", headers=owner[1], json={"operating_system": None}
    )
    assert patched.status_code == 200
    assert patched.json()["os_family"] == os_family


async def test_new_server_requires_os_family(client, db_session, owner, customer):
    response = await client.post(collection(customer), headers=owner[1], json={"name": "Sem SO"})
    assert response.status_code == 422
    assert any(error["loc"] == ["body", "os_family"] for error in response.json()["detail"])
    assert await count_servers(db_session, customer) == 0


@pytest.mark.parametrize("method", ["POST", "PATCH"])
@pytest.mark.parametrize("value", [None, "", "linux", "MACOS", "Ubuntu 24.04"])
async def test_invalid_os_family_is_rejected(
    client, db_session, owner, customer, server_factory, method, value
):
    server = await server_factory(customer)
    path = collection(customer) if method == "POST" else f"/servers/{server.id}"
    response = await client.request(
        method, path, headers=owner[1], json={"name": "Novo nome", "os_family": value}
    )
    assert response.status_code == 422, response.text
    await db_session.refresh(server)
    assert server.os_family == "LINUX"
    assert server.name == "Servidor ERP"
    assert await count_servers(db_session, customer) == 1


@pytest.mark.parametrize("os_family", ["WINDOWS", "LINUX"])
async def test_legacy_server_can_be_read_and_classified(
    client, db_session, owner, customer, server_factory, os_family
):
    server = await server_factory(customer, os_family=None, operating_system="Descrição legada")
    fetched = await client.get(f"/servers/{server.id}", headers=owner[1])
    assert fetched.status_code == 200
    assert fetched.json()["os_family"] is None
    response = await client.patch(
        f"/servers/{server.id}", headers=owner[1], json={"os_family": os_family}
    )
    assert response.status_code == 200
    await db_session.refresh(server)
    assert server.os_family == os_family
    assert server.operating_system == "Descrição legada"


async def test_create_server_defaults(client, owner, customer):
    response = await client.post(collection(customer), headers=owner[1], json={"os_family": "LINUX", "name": "  ERP  "})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "ERP"
    assert body["server_type"] == "VPS"
    assert body["is_active"] is True
    for field in ("hostname", "ip_address", "operating_system", "description"):
        assert body[field] is None


@pytest.mark.parametrize("server_type", list(ServerType))
async def test_create_supported_server_types(client, owner, customer, server_type):
    response = await client.post(collection(customer), headers=owner[1],
                                 json={"os_family": "LINUX", "name": "Servidor", "server_type": server_type.value})
    assert response.status_code == 201, response.text
    assert response.json()["server_type"] == server_type.value


async def test_duplicate_name_in_same_customer_rejected(client, db_session, owner, customer):
    first = await client.post(collection(customer), headers=owner[1], json={"os_family": "LINUX", "name": "ERP"})
    duplicate = await client.post(collection(customer), headers=owner[1], json={"os_family": "LINUX", "name": "ERP"})
    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert await count_servers(db_session, customer) == 1


async def test_same_name_allowed_in_different_customers(client, owner, customer, customer_factory):
    other_customer = await customer_factory(owner[0])
    for target in (customer, other_customer):
        response = await client.post(collection(target), headers=owner[1], json={"os_family": "LINUX", "name": "ERP"})
        assert response.status_code == 201, response.text


@pytest.mark.parametrize("foreign", [False, True], ids=["missing", "other-owner"])
async def test_cannot_create_in_unowned_customer(
    client, db_session, owner, owner_factory, customer_factory, foreign
):
    other, _ = await owner_factory()
    target = await customer_factory(other)
    target_id = target.id if foreign else uuid4()
    response = await client.post(f"/customers/{target_id}/servers", headers=owner[1], json={"os_family": "LINUX", "name": "ERP"})
    assert response.status_code == 404, response.text
    assert await count_servers(db_session, target) == 0


async def test_server_limit_is_global_across_customers(
    client, db_session, free_plan, owner, customer, customer_factory
):
    free_plan.max_servers = 2
    await db_session.flush()
    other = await customer_factory(owner[0])
    for target in (customer, other):
        response = await client.post(collection(target), headers=owner[1], json={"os_family": "LINUX", "name": "ERP"})
        assert response.status_code == 201, response.text
    blocked = await client.post(collection(other), headers=owner[1], json={"os_family": "LINUX", "name": "Novo servidor"})
    assert blocked.status_code == 403, blocked.text
    assert await count_servers(db_session, customer) == 1
    assert await count_servers(db_session, other) == 1


async def test_other_users_servers_do_not_consume_limit(
    client, db_session, free_plan, owner, customer, owner_factory, customer_factory, server_factory
):
    free_plan.max_servers = 1
    other, _ = await owner_factory()
    other_customer = await customer_factory(other)
    await server_factory(other_customer)
    response = await client.post(collection(customer), headers=owner[1], json={"os_family": "LINUX", "name": "ERP"})
    assert response.status_code == 201, response.text


async def test_inactive_server_still_counts_toward_limit(
    client, free_plan, owner, customer, server_factory
):
    free_plan.max_servers = 1
    await server_factory(customer, is_active=False)
    response = await client.post(collection(customer), headers=owner[1], json={"os_family": "LINUX", "name": "Novo servidor"})
    assert response.status_code == 403, response.text


@pytest.mark.parametrize("status,expected", [
    (SubscriptionStatus.ACTIVE, 201), (SubscriptionStatus.TRIAL, 201),
    (SubscriptionStatus.PAST_DUE, 403), (SubscriptionStatus.CANCELED, 403),
    (SubscriptionStatus.EXPIRED, 403),
])
async def test_subscription_status_controls_creation(
    client, db_session, owner_factory, customer_factory, status, expected
):
    user, headers = await owner_factory(status)
    target = await customer_factory(user)
    response = await client.post(collection(target), headers=headers, json={"os_family": "LINUX", "name": "ERP"})
    assert response.status_code == expected, response.text
    assert await count_servers(db_session, target) == (1 if expected == 201 else 0)


async def test_get_owned_server(client, owner, customer, server_factory):
    server = await server_factory(customer, description="Informação privada")
    response = await client.get(f"/servers/{server.id}", headers=owner[1])
    assert response.status_code == 200, response.text
    assert response.json()["id"] == str(server.id)
    assert response.json()["description"] == "Informação privada"


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
@pytest.mark.parametrize("foreign", [False, True], ids=["missing", "other-owner"])
async def test_unowned_server_returns_404_without_mutation(
    client, db_session, owner, owner_factory, customer_factory, server_factory, method, foreign
):
    other, _ = await owner_factory()
    target = await customer_factory(other)
    server = await server_factory(target)
    target_id = server.id if foreign else uuid4()
    kwargs = {"json": {"name": "Alterado"}} if method == "PATCH" else {}
    response = await client.request(method, f"/servers/{target_id}", headers=owner[1], **kwargs)
    assert response.status_code == 404, response.text
    await db_session.refresh(server)
    assert server.name == "Servidor ERP"
    assert server.customer_id == target.id


async def test_list_filters_customer_and_owner(
    client, owner, customer, owner_factory, customer_factory, server_factory
):
    owned = await server_factory(customer)
    sibling = await customer_factory(owner[0])
    await server_factory(sibling)
    other, _ = await owner_factory()
    foreign = await customer_factory(other)
    await server_factory(foreign)
    response = await client.get(collection(customer), headers=owner[1])
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(owned.id)]
    # Contrato atual: coleção de cliente alheio/inexistente retorna lista vazia.
    for path in (collection(foreign), f"/customers/{uuid4()}/servers"):
        response = await client.get(path, headers=owner[1])
        assert response.status_code == 200
        assert response.json() == []


async def test_list_empty_customer(client, owner, customer):
    response = await client.get(collection(customer), headers=owner[1])
    assert response.status_code == 200
    assert response.json() == []


async def test_list_pagination_newest_first(client, owner, customer, server_factory):
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    servers = [await server_factory(customer, name=f"Servidor {i}", created_at=start + timedelta(days=i))
               for i in range(3)]
    response = await client.get(collection(customer) + "?limit=2", headers=owner[1])
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(servers[2].id), str(servers[1].id)]
    response = await client.get(collection(customer) + "?skip=1&limit=1", headers=owner[1])
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(servers[1].id)]


@pytest.mark.parametrize("query", ["skip=-1", "limit=0", "limit=101"])
async def test_invalid_pagination(client, owner, customer, query):
    response = await client.get(collection(customer) + f"?{query}", headers=owner[1])
    assert response.status_code == 422


@pytest.mark.parametrize("ip", ["192.0.2.20", "2001:db8::20"], ids=["ipv4", "ipv6"])
async def test_patch_persists_fields_and_preserves_omitted(
    client, db_session, owner, customer, server_factory, ip
):
    server = await server_factory(customer, hostname="original.example.com", description="Original")
    payload = dict(name="Novo nome", ip_address=ip, server_type="DATABASE", is_active=False, operating_system="Linux")
    response = await client.patch(f"/servers/{server.id}", headers=owner[1], json=payload)
    assert response.status_code == 200, response.text
    await db_session.refresh(server)
    for field, value in payload.items():
        assert response.json()[field] == value
        assert getattr(server, field) == value
    assert server.hostname == "original.example.com"
    assert server.description == "Original"
    assert server.customer_id == customer.id


async def test_patch_clears_nullable_fields(client, db_session, owner, customer, server_factory):
    server = await server_factory(customer, hostname="erp.example.com", ip_address="192.0.2.1",
                                  operating_system="Linux", description="Original")
    payload = dict.fromkeys(("hostname", "ip_address", "operating_system", "description"))
    response = await client.patch(f"/servers/{server.id}", headers=owner[1], json=payload)
    assert response.status_code == 200, response.text
    await db_session.refresh(server)
    for field in payload:
        assert response.json()[field] is None
        assert getattr(server, field) is None


@pytest.mark.parametrize("payload", [{}, {"name": "Servidor ERP"}])
async def test_patch_empty_or_same_name(client, owner, customer, server_factory, payload):
    server = await server_factory(customer)
    response = await client.patch(f"/servers/{server.id}", headers=owner[1], json=payload)
    assert response.status_code == 200
    assert response.json()["name"] == "Servidor ERP"


async def test_patch_duplicate_name_rejected(client, db_session, owner, customer, server_factory):
    await server_factory(customer, name="ERP")
    server = await server_factory(customer, name="Banco")
    response = await client.patch(f"/servers/{server.id}", headers=owner[1], json={"os_family": "LINUX", "name": "ERP"})
    assert response.status_code == 409
    await db_session.refresh(server)
    assert server.name == "Banco"


async def test_patch_name_used_in_other_customer_allowed(
    client, owner, customer, customer_factory, server_factory
):
    sibling = await customer_factory(owner[0])
    await server_factory(sibling, name="ERP")
    server = await server_factory(customer)
    response = await client.patch(f"/servers/{server.id}", headers=owner[1], json={"os_family": "LINUX", "name": "ERP"})
    assert response.status_code == 200
    assert response.json()["name"] == "ERP"


@pytest.mark.parametrize("field", ["name", "server_type", "is_active", "os_family"])
async def test_patch_rejects_null_required_fields(client, db_session, owner, customer, server_factory, field):
    server = await server_factory(customer)
    response = await client.patch(f"/servers/{server.id}", headers=owner[1], json={field: None})
    assert response.status_code == 422, response.text
    await db_session.refresh(server)
    assert getattr(server, field) is not None


@pytest.mark.parametrize("method", ["POST", "PATCH"])
@pytest.mark.parametrize("invalid", [
    {"name": "x"}, {"name": "   "}, {"name": "x" * 121},
    {"server_type": "INVALID"}, {"ip_address": "999.999.999.999"},
    {"hostname": "x" * 256}, {"operating_system": "x" * 101}, {"description": "x" * 2001},
    {"customer_id": str(uuid4())}, {"user_id": str(uuid4())}, {"extra": "value"},
], ids=["short-name", "blank-name", "long-name", "type", "ip", "hostname", "os", "description",
        "customer-injection", "owner-injection", "extra"])
async def test_invalid_payload_does_not_mutate(
    client, db_session, owner, customer, server_factory, method, invalid
):
    server = await server_factory(customer)
    path = collection(customer) if method == "POST" else f"/servers/{server.id}"
    response = await client.request(method, path, headers=owner[1], json={"os_family": "LINUX", "name": "Novo servidor", **invalid})
    assert response.status_code == 422, response.text
    await db_session.refresh(server)
    assert server.name == "Servidor ERP"
    assert server.customer_id == customer.id
    assert await count_servers(db_session, customer) == 1


async def test_delete_frees_plan_slot(client, db_session, free_plan, owner, customer, server_factory):
    free_plan.max_servers = 1
    server = await server_factory(customer)
    response = await client.delete(f"/servers/{server.id}", headers=owner[1])
    assert response.status_code == 204
    assert response.content == b""
    assert await count_servers(db_session, customer) == 0
    missing = await client.get(f"/servers/{server.id}", headers=owner[1])
    assert missing.status_code == 404
    replacement = await client.post(collection(customer), headers=owner[1], json={"os_family": "LINUX", "name": "Substituto"})
    assert replacement.status_code == 201, replacement.text


async def test_delete_cascades_agent_metrics_alerts_but_preserves_other_server(
    client, db_session, owner, customer, server_factory
):
    servers = [await server_factory(customer, name=name) for name in ("Excluir", "Preservar")]
    for server in servers:
        db_session.add_all([
            Agent(server_id=server.id, token_hash=uuid4().hex),
            Metric(server_id=server.id, cpu_usage=10, memory_usage=20, disk_usage=30,
                   network_in_bytes=0, network_out_bytes=0, process_count=1, uptime_seconds=100),
            Alert(server_id=server.id, severity=AlertSeverity.WARNING, metric_name="cpu_usage",
                  metric_value=90, threshold=80, title="CPU elevada"),
        ])
    await db_session.flush()
    response = await client.delete(f"/servers/{servers[0].id}", headers=owner[1])
    assert response.status_code == 204, response.text
    for model in (Agent, Metric, Alert):
        for server, expected in zip(servers, (0, 1)):
            assert await db_session.scalar(
                select(func.count()).select_from(model).where(model.server_id == server.id)
            ) == expected
    assert await count_servers(db_session, customer) == 1
    await db_session.refresh(customer)


@pytest.mark.parametrize("method,path", [
    ("POST", "/customers/{id}/servers"), ("GET", "/customers/{id}/servers"),
    ("GET", "/servers/{id}"), ("PATCH", "/servers/{id}"), ("DELETE", "/servers/{id}"),
])
async def test_server_routes_require_authentication(client, method, path):
    kwargs = {"json": {"name": "ERP"}} if method in ("POST", "PATCH") else {}
    response = await client.request(method, path.format(id=uuid4()), **kwargs)
    assert response.status_code == 401, response.text
