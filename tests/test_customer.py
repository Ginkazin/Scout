from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.core.security import DUMMY_PASSWORD_HASH, create_access_token
from app.models.customer import Customer
from app.models.server import Server
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User, UserRole


@pytest_asyncio.fixture
async def account_factory(db_session, free_plan):
    async def create_account(status=SubscriptionStatus.ACTIVE):
        user = User(
            name="Usuário de teste",
            email=f"{uuid4().hex}@example.com",
            password_hash=DUMMY_PASSWORD_HASH,
            role=UserRole.ADMIN,
        )
        db_session.add(user)
        await db_session.flush()
        db_session.add(
            Subscription(user_id=user.id, plan_id=free_plan.id, status=status)
        )
        await db_session.flush()
        headers = {"Authorization": f"Bearer {create_access_token(user.id)}"}
        return user, headers

    return create_account


@pytest_asyncio.fixture
async def account(account_factory):
    return await account_factory()


@pytest_asyncio.fixture
async def customer_factory(db_session):
    async def create_customer(user, **fields):
        customer = Customer(
            user_id=user.id,
            **{"name": "Empresa Teste", **fields},
        )
        db_session.add(customer)
        await db_session.flush()
        return customer

    return create_customer


async def customer_count(db_session, user_id):
    return await db_session.scalar(
        select(func.count()).select_from(Customer).where(Customer.user_id == user_id)
    )


async def test_create_customer_persists_owner_and_fields(client, db_session, account):
    user, headers = account
    payload = {
        "name": "Empresa ABC",
        "company": "ABC Tecnologia",
        "email": "contato@example.com",
        "phone": "85999999999",
        "notes": "Servidor ERP",
    }

    response = await client.post("/customers", headers=headers, json=payload)

    assert response.status_code == 201, response.text
    body = response.json()
    for field, value in payload.items():
        assert body[field] == value
    assert body["is_active"] is True
    assert body["created_at"] and body["updated_at"]
    assert "user_id" not in body
    customer = await db_session.get(Customer, UUID(body["id"]))
    assert customer.user_id == user.id
    for field, value in payload.items():
        assert getattr(customer, field) == value


async def test_create_customer_minimal_payload(client, account):
    _, headers = account
    response = await client.post(
        "/customers", headers=headers, json={"name": "  Empresa ABC  "}
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Empresa ABC"
    assert body["is_active"] is True
    for field in ("company", "email", "phone", "notes"):
        assert body[field] is None


async def test_create_duplicate_customer(client, db_session, account, free_plan):
    user, headers = account
    free_plan.max_customers = 3
    await db_session.flush()
    payload = {"name": "Empresa ABC"}
    first = await client.post("/customers", headers=headers, json=payload)
    duplicate = await client.post("/customers", headers=headers, json=payload)
    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert await customer_count(db_session, user.id) == 1


async def test_same_customer_name_allowed_for_different_users(client, account_factory):
    for _ in range(2):
        _, headers = await account_factory()
        response = await client.post(
            "/customers", headers=headers, json={"name": "Empresa ABC"}
        )
        assert response.status_code == 201, response.text


async def test_customer_limit_blocks_creation(client, db_session, account):
    user, headers = account
    first = await client.post("/customers", headers=headers, json={"name": "Empresa A"})
    blocked = await client.post("/customers", headers=headers, json={"name": "Empresa B"})
    assert first.status_code == 201
    assert blocked.status_code == 403
    assert await customer_count(db_session, user.id) == 1


async def test_inactive_customer_still_counts_toward_limit(
    client, db_session, account, customer_factory
):
    user, headers = account
    await customer_factory(user, is_active=False)
    response = await client.post(
        "/customers", headers=headers, json={"name": "Novo cliente"}
    )
    assert response.status_code == 403
    assert await customer_count(db_session, user.id) == 1


@pytest.mark.parametrize("status", [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL])
async def test_allowed_subscription_can_create(client, account_factory, status):
    _, headers = await account_factory(status=status)
    response = await client.post(
        "/customers", headers=headers, json={"name": "Empresa ABC"}
    )
    assert response.status_code == 201, response.text


@pytest.mark.parametrize(
    "status",
    [SubscriptionStatus.PAST_DUE, SubscriptionStatus.CANCELED, SubscriptionStatus.EXPIRED],
)
async def test_blocked_subscription_cannot_create(
    client, db_session, account_factory, status
):
    user, headers = await account_factory(status=status)
    response = await client.post(
        "/customers", headers=headers, json={"name": "Empresa ABC"}
    )
    assert response.status_code == 403, response.text
    assert await customer_count(db_session, user.id) == 0


async def test_list_empty_customers(client, account):
    _, headers = account
    response = await client.get("/customers", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


async def test_list_only_owned_customers(
    client, account, account_factory, customer_factory
):
    user, headers = account
    other, _ = await account_factory()
    owned = await customer_factory(user)
    await customer_factory(other)
    response = await client.get("/customers", headers=headers)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(owned.id)]


async def test_list_pagination_newest_first(client, account, customer_factory):
    user, headers = account
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    customers = [
        await customer_factory(
            user, name=f"Empresa {index}", created_at=start + timedelta(days=index)
        )
        for index in range(3)
    ]
    response = await client.get("/customers?skip=1&limit=1", headers=headers)
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(customers[1].id)]
    response = await client.get("/customers?limit=2", headers=headers)
    assert [item["id"] for item in response.json()] == [
        str(customers[2].id), str(customers[1].id)
    ]


@pytest.mark.parametrize("query", ["skip=-1", "limit=0", "limit=101"])
async def test_invalid_pagination(client, account, query):
    _, headers = account
    response = await client.get(f"/customers?{query}", headers=headers)
    assert response.status_code == 422


async def test_get_owned_customer(client, account, customer_factory):
    user, headers = account
    customer = await customer_factory(user, notes="Observação privada")
    response = await client.get(f"/customers/{customer.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == str(customer.id)
    assert response.json()["notes"] == "Observação privada"


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
@pytest.mark.parametrize("foreign", [False, True], ids=["missing", "other-owner"])
async def test_customer_access_returns_404_without_changing_foreign_data(
    client, db_session, account, account_factory, customer_factory, method, foreign
):
    _, headers = account
    other, _ = await account_factory()
    customer = await customer_factory(other, name="Cliente protegido")
    target_id = customer.id if foreign else uuid4()
    kwargs = {"json": {"name": "Nome alterado"}} if method == "PATCH" else {}
    response = await client.request(
        method, f"/customers/{target_id}", headers=headers, **kwargs
    )
    assert response.status_code == 404, response.text
    await db_session.refresh(customer)
    assert customer.name == "Cliente protegido"
    assert customer.user_id == other.id


async def test_patch_updates_fields_and_preserves_omitted_fields(
    client, db_session, account, customer_factory
):
    user, headers = account
    customer = await customer_factory(user, company="Empresa original", notes="Nota")
    payload = {"name": "Novo nome", "email": "novo@example.com", "is_active": False}
    response = await client.patch(f"/customers/{customer.id}", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    await db_session.refresh(customer)
    for field, value in payload.items():
        assert response.json()[field] == value
        assert getattr(customer, field) == value
    assert customer.company == "Empresa original"
    assert customer.notes == "Nota"
    assert customer.user_id == user.id


async def test_patch_clears_nullable_fields(client, db_session, account, customer_factory):
    user, headers = account
    customer = await customer_factory(
        user, company="Empresa", email="contato@example.com", phone="123", notes="Nota"
    )
    payload = dict.fromkeys(("company", "email", "phone", "notes"))
    response = await client.patch(f"/customers/{customer.id}", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    await db_session.refresh(customer)
    for field in payload:
        assert response.json()[field] is None
        assert getattr(customer, field) is None


@pytest.mark.parametrize("payload", [{}, {"name": "Empresa Teste"}])
async def test_patch_noop_and_same_name(client, account, customer_factory, payload):
    user, headers = account
    customer = await customer_factory(user)
    response = await client.patch(f"/customers/{customer.id}", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Empresa Teste"


async def test_patch_duplicate_name_rejected(client, db_session, account, customer_factory):
    user, headers = account
    await customer_factory(user, name="Empresa A")
    customer = await customer_factory(user, name="Empresa B")
    response = await client.patch(
        f"/customers/{customer.id}", headers=headers, json={"name": "Empresa A"}
    )
    assert response.status_code == 409
    await db_session.refresh(customer)
    assert customer.name == "Empresa B"


async def test_patch_can_use_other_users_customer_name(
    client, account, account_factory, customer_factory
):
    user, headers = account
    other, _ = await account_factory()
    customer = await customer_factory(user, name="Empresa A")
    await customer_factory(other, name="Empresa B")
    response = await client.patch(
        f"/customers/{customer.id}", headers=headers, json={"name": "Empresa B"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Empresa B"


@pytest.mark.parametrize("field", ["name", "is_active"])
async def test_patch_rejects_null_required_fields(client, account, customer_factory, field):
    user, headers = account
    customer = await customer_factory(user)
    response = await client.patch(
        f"/customers/{customer.id}", headers=headers, json={field: None}
    )
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("method", ["POST", "PATCH"])
@pytest.mark.parametrize(
    "invalid",
    [
        {"name": "ab"},
        {"name": " " * 4},
        {"name": "x" * 121},
        {"company": "x" * 121},
        {"email": "invalid-email"},
        {"phone": "1" * 31},
        {"notes": "x" * 2001},
        {"user_id": str(uuid4())},
        {"unexpected": "value"},
    ],
    ids=["short-name", "blank-name", "long-name", "company", "email", "phone", "notes", "owner-injection", "extra-field"],
)
async def test_invalid_payload_does_not_modify_data(
    client, db_session, account, customer_factory, method, invalid
):
    user, headers = account
    customer = await customer_factory(user)
    path = "/customers" if method == "POST" else f"/customers/{customer.id}"
    response = await client.request(
        method, path, headers=headers, json={"name": "Empresa nova", **invalid}
    )
    assert response.status_code == 422, response.text
    await db_session.refresh(customer)
    assert customer.name == "Empresa Teste"
    assert customer.user_id == user.id
    assert await customer_count(db_session, user.id) == 1


async def test_delete_customer_and_reuse_plan_slot(
    client, db_session, account, customer_factory
):
    user, headers = account
    customer = await customer_factory(user)
    response = await client.delete(f"/customers/{customer.id}", headers=headers)
    assert response.status_code == 204
    assert response.content == b""
    assert await customer_count(db_session, user.id) == 0
    missing = await client.get(f"/customers/{customer.id}", headers=headers)
    assert missing.status_code == 404
    replacement = await client.post(
        "/customers", headers=headers, json={"name": "Cliente substituto"}
    )
    assert replacement.status_code == 201, replacement.text


async def test_delete_customer_cascades_servers(
    client, db_session, account, customer_factory
):
    user, headers = account
    customer = await customer_factory(user)
    server = Server(customer_id=customer.id, name="Servidor ERP")
    db_session.add(server)
    await db_session.flush()
    response = await client.delete(f"/customers/{customer.id}", headers=headers)
    assert response.status_code == 204, response.text
    assert await db_session.scalar(
        select(func.count()).select_from(Server).where(Server.id == server.id)
    ) == 0


@pytest.mark.parametrize(
    "method,path",
    [("POST", "/customers"), ("GET", "/customers"), ("GET", "/customers/{id}"),
     ("PATCH", "/customers/{id}"), ("DELETE", "/customers/{id}")],
)
async def test_customer_routes_require_authentication(client, method, path):
    kwargs = {"json": {"name": "Empresa ABC"}} if method in ("POST", "PATCH") else {}
    response = await client.request(method, path.format(id=uuid4()), **kwargs)
    assert response.status_code == 401, response.text
