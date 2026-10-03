"""Agent: contrato HTTP, credenciais e concorrência em PostgreSQL.

Os testes de concorrência usam sessões independentes e dados próprios commitados,
com limpeza explícita; os demais usam a transação isolada do conftest.
"""

import asyncio
import hashlib
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_security import generate_agent_token, parse_agent_token, verify_agent_secret
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import DUMMY_PASSWORD_HASH, create_access_token
from app.models.agent import Agent, AgentStatus
from app.models.alert import Alert, AlertSeverity
from app.models.customer import Customer
from app.models.metric import Metric
from app.models.server import Server
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User, UserRole
from app.repositories.agent_repository import AgentRepository
from app.repositories.server_repository import ServerRepository
from app.schemas.agent_schema import AgentHeartbeat
from app.services.agent_service import AgentService


@pytest_asyncio.fixture
async def owner_factory(db_session, free_plan):
    async def create():
        user = User(name="Agent Teste", email=f"{uuid4().hex}@example.com",
                    password_hash=DUMMY_PASSWORD_HASH, role=UserRole.ADMIN)
        db_session.add(user)
        await db_session.flush()
        db_session.add(Subscription(user_id=user.id, plan_id=free_plan.id, status=SubscriptionStatus.ACTIVE))
        customer = Customer(user_id=user.id, name="Empresa Agent")
        db_session.add(customer)
        await db_session.flush()
        server = Server(customer_id=customer.id, name="Servidor Agent")
        db_session.add(server)
        await db_session.flush()
        return user, server, {"Authorization": f"Bearer {create_access_token(user.id)}"}
    return create


@pytest_asyncio.fixture
async def owner(owner_factory):
    return await owner_factory()


@pytest_asyncio.fixture
async def created_agent(client, db_session, owner):
    response = await client.post(f"/servers/{owner[1].id}/agent", headers=owner[2])
    assert response.status_code == 201, response.text
    body = response.json()
    agent = await db_session.get(Agent, UUID(body["id"]))
    return agent, body["token"]


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def assert_no_secrets(response):
    assert "token" not in response.json()
    assert "token_hash" not in response.json()


async def heartbeat(client, token, **payload):
    return await client.post("/agent/heartbeat", headers=bearer(token),
                             json={"version": "2.0.0", **payload})


async def test_create_pending_agent_and_store_only_hash(client, db_session, owner):
    response = await client.post(f"/servers/{owner[1].id}/agent", headers=owner[2])
    assert response.status_code == 201, response.text
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["server_id"] == str(owner[1].id)
    assert body["status"] == "PENDING"
    assert body["last_seen_at"] is None
    assert body["auto_update"] is False
    assert "token_hash" not in body
    agent_id, secret = parse_agent_token(body["token"])
    assert str(agent_id) == body["id"]
    agent = await db_session.get(Agent, agent_id)
    assert agent.token_hash == hashlib.sha256(secret.encode("ascii")).hexdigest()
    assert agent.token_hash not in (body["token"], secret)


async def test_duplicate_creation_preserves_original_credential(client, db_session, owner, created_agent):
    agent, token = created_agent
    original_hash = agent.token_hash
    response = await client.post(f"/servers/{owner[1].id}/agent", headers=owner[2])
    assert response.status_code == 409
    assert_no_secrets(response)
    await db_session.refresh(agent)
    assert agent.token_hash == original_hash
    assert await db_session.scalar(select(func.count()).select_from(Agent).where(Agent.server_id == owner[1].id)) == 1
    assert (await heartbeat(client, token)).status_code == 200


async def test_agents_receive_independent_tokens(client, owner, owner_factory, created_agent):
    agent, token = created_agent
    _, server, headers = await owner_factory()
    response = await client.post(f"/servers/{server.id}/agent", headers=headers)
    assert response.status_code == 201
    other_token = response.json()["token"]
    assert parse_agent_token(token)[1] != parse_agent_token(other_token)[1]
    # Um segredo de outro Agent não autentica com o ID do primeiro.
    mixed = f"scout_{agent.id}.{parse_agent_token(other_token)[1]}"
    assert (await heartbeat(client, mixed)).status_code == 401


@pytest.mark.parametrize("foreign", [False, True], ids=["missing", "other-owner"])
async def test_create_requires_owned_server(client, db_session, owner, owner_factory, foreign):
    _, other_server, _ = await owner_factory()
    target = other_server.id if foreign else uuid4()
    response = await client.post(f"/servers/{target}/agent", headers=owner[2])
    assert response.status_code == 404
    assert await db_session.scalar(select(func.count()).select_from(Agent)) == 0


async def test_get_owned_agent_without_exposing_token(client, owner, created_agent):
    agent, _ = created_agent
    response = await client.get(f"/agents/{agent.id}", headers=owner[2])
    assert response.status_code == 200
    assert response.json()["id"] == str(agent.id)
    assert response.json()["status"] == "PENDING"
    assert_no_secrets(response)


@pytest.mark.parametrize("operation", ["get", "disable", "enable"])
@pytest.mark.parametrize("foreign", [False, True], ids=["missing", "other-owner"])
async def test_management_ownership_returns_404(
    client, db_session, owner_factory, created_agent, operation, foreign
):
    agent, _ = created_agent
    _, _, other_headers = await owner_factory()
    target = agent.id if foreign else uuid4()
    path = f"/agents/{target}" + (f"/{operation}" if operation != "get" else "")
    response = await client.request("GET" if operation == "get" else "POST", path, headers=other_headers)
    assert response.status_code == 404
    await db_session.refresh(agent)
    assert agent.status == AgentStatus.PENDING
    assert agent.last_seen_at is None


@pytest.mark.parametrize("state", [AgentStatus.PENDING, AgentStatus.ONLINE, AgentStatus.OFFLINE])
async def test_heartbeat_from_allowed_states_updates_only_target(
    client, db_session, owner_factory, created_agent, state
):
    agent, token = created_agent
    old = datetime(2020, 1, 1, tzinfo=timezone.utc)
    agent.status, agent.last_seen_at = state, old
    await db_session.flush()
    _, other_server, other_headers = await owner_factory()
    other_response = await client.post(f"/servers/{other_server.id}/agent", headers=other_headers)
    other = await db_session.get(Agent, UUID(other_response.json()["id"]))
    before = await db_session.scalar(select(func.clock_timestamp()))
    response = await heartbeat(client, token)
    after = await db_session.scalar(select(func.clock_timestamp()))
    assert response.status_code == 200, response.text
    assert_no_secrets(response)
    assert response.json()["status"] == "ONLINE"
    assert response.json()["version"] == "2.0.0"
    await db_session.refresh(agent)
    assert agent.status == AgentStatus.ONLINE
    assert agent.version == "2.0.0"
    assert before <= agent.last_seen_at <= after
    assert agent.updated_at >= before
    await db_session.refresh(other)
    assert other.status == AgentStatus.PENDING
    assert other.last_seen_at is None


async def test_repeated_heartbeat_refreshes_timestamp(client, db_session, created_agent):
    agent, token = created_agent
    assert (await heartbeat(client, token)).status_code == 200
    await db_session.refresh(agent)
    first = agent.last_seen_at
    response = await heartbeat(client, token, version="2.1.0")
    assert response.status_code == 200
    await db_session.refresh(agent)
    assert agent.last_seen_at > first
    assert agent.version == "2.1.0"


@pytest.mark.parametrize("state", list(AgentStatus))
async def test_disable_is_idempotent_and_blocks_heartbeat(client, db_session, owner, created_agent, state):
    agent, token = created_agent
    old = datetime(2020, 1, 1, tzinfo=timezone.utc)
    agent.status, agent.last_seen_at = state, old
    await db_session.flush()
    for _ in range(2):
        response = await client.post(f"/agents/{agent.id}/disable", headers=owner[2])
        assert response.status_code == 200
        assert response.json()["status"] == "DISABLED"
        assert_no_secrets(response)
    rejected = await heartbeat(client, token)
    assert rejected.status_code == 401
    await db_session.refresh(agent)
    assert agent.status == AgentStatus.DISABLED
    assert agent.last_seen_at == old
    assert agent.version == "1.0.0"


async def test_enable_waits_for_new_heartbeat_and_preserves_token(client, db_session, owner, created_agent):
    agent, token = created_agent
    await heartbeat(client, token)
    await db_session.refresh(agent)
    previous_seen, previous_hash = agent.last_seen_at, agent.token_hash
    assert (await client.post(f"/agents/{agent.id}/disable", headers=owner[2])).status_code == 200
    response = await client.post(f"/agents/{agent.id}/enable", headers=owner[2])
    assert response.status_code == 200
    assert response.json()["status"] == "PENDING"
    assert_no_secrets(response)
    await db_session.refresh(agent)
    assert agent.last_seen_at == previous_seen
    assert agent.token_hash == previous_hash
    assert (await heartbeat(client, token)).status_code == 200
    await db_session.refresh(agent)
    assert agent.status == AgentStatus.ONLINE


@pytest.mark.parametrize("state", [AgentStatus.PENDING, AgentStatus.ONLINE, AgentStatus.OFFLINE])
async def test_enable_rejects_non_disabled_agent(client, db_session, owner, created_agent, state):
    agent, _ = created_agent
    agent.status = state
    await db_session.flush()
    response = await client.post(f"/agents/{agent.id}/enable", headers=owner[2])
    assert response.status_code == 409
    await db_session.refresh(agent)
    assert agent.status == state


@pytest.mark.parametrize("case", ["missing", "empty-bearer", "basic", "malformed", "wrong-secret", "unknown-id", "user-jwt"])
async def test_heartbeat_rejects_invalid_credentials(client, db_session, owner, created_agent, case):
    agent, token = created_agent
    headers = bearer(token)
    if case == "missing":
        headers = {}
    elif case == "empty-bearer":
        headers = {"Authorization": "Bearer"}
    elif case == "basic":
        headers = {"Authorization": f"Basic {token}"}
    elif case == "malformed":
        headers = bearer("not-an-agent-token")
    elif case == "wrong-secret":
        headers = bearer(generate_agent_token(agent.id)[0])
    elif case == "unknown-id":
        headers = bearer(generate_agent_token(uuid4())[0])
    elif case == "user-jwt":
        headers = owner[2]
    response = await client.post("/agent/heartbeat", headers=headers, json={"version": "2.0.0"})
    assert response.status_code == 401, response.text
    assert response.headers["www-authenticate"] == "Bearer"
    assert_no_secrets(response)
    await db_session.refresh(agent)
    assert agent.status == AgentStatus.PENDING
    assert agent.last_seen_at is None


@pytest.mark.parametrize("payload", [{}, {"version": ""}, {"version": "   "}, {"version": "x" * 21},
    {"version": None}, {"version": "1.0", "status": "ONLINE"},
    {"version": "1.0", "server_id": str(uuid4())}, {"version": "1.0", "agent_id": str(uuid4())},
    {"version": "1.0", "last_seen_at": "2030-01-01T00:00:00Z"}],
    ids=["missing", "empty", "blank", "long", "null", "status-injection", "server-injection", "agent-injection", "timestamp-injection"])
async def test_heartbeat_validation_preserves_agent(client, db_session, created_agent, payload):
    agent, token = created_agent
    response = await client.post("/agent/heartbeat", headers=bearer(token), json=payload)
    assert response.status_code == 422, response.text
    await db_session.refresh(agent)
    assert agent.status == AgentStatus.PENDING
    assert agent.last_seen_at is None


@pytest.mark.parametrize("operation", ["create", "get", "disable", "enable"])
@pytest.mark.parametrize("credential", ["missing", "agent-token"])
async def test_management_requires_user_jwt(client, owner, created_agent, operation, credential):
    agent, token = created_agent
    path = f"/servers/{owner[1].id}/agent" if operation == "create" else f"/agents/{agent.id}"
    if operation in ("disable", "enable"):
        path += f"/{operation}"
    response = await client.request("GET" if operation == "get" else "POST", path,
                                    headers={} if credential == "missing" else bearer(token))
    assert response.status_code == 401, response.text


def test_token_generation_roundtrip_and_secret_hash():
    agent_id = uuid4()
    token, digest = generate_agent_token(agent_id)
    parsed_id, secret = parse_agent_token(token)
    assert parsed_id == agent_id
    assert len(secret) == 43
    assert len(digest) == 64
    assert digest == hashlib.sha256(secret.encode("ascii")).hexdigest()
    assert verify_agent_secret(secret, digest)
    _, other_secret = parse_agent_token(generate_agent_token(agent_id)[0])
    assert not verify_agent_secret(other_secret, digest)


@pytest.mark.parametrize("case", ["empty", "prefix", "separator", "uuid", "short", "long", "unicode", "space"])
def test_parser_rejects_malformed_tokens(case):
    token, _ = generate_agent_token(uuid4())
    if case == "empty": token = ""
    elif case == "prefix": token = "wrong_" + token[6:]
    elif case == "separator": token = token.replace(".", "_")
    elif case == "uuid": token = "scout_" + "z" * 36 + token[42:]
    elif case == "short": token = token[:-1]
    elif case == "long": token += "x"
    elif case == "unicode": token = token[:-1] + "é"
    elif case == "space": token = token[:-1] + " "
    with pytest.raises(ValueError):
        parse_agent_token(token)


@pytest.mark.parametrize("secret", ["", "a" * 42, "a" * 44, "é" * 43, " " * 43])
def test_verify_rejects_malformed_secret(secret):
    assert not verify_agent_secret(secret, "0" * 64)


@pytest.mark.parametrize("state", list(AgentStatus))
async def test_delete_owned_agent_from_any_state(
    client, db_session, owner, created_agent, state
):
    agent, token = created_agent
    agent.status = state
    await db_session.flush()
    agent_id = agent.id
    response = await client.delete(f"/agents/{agent_id}", headers=owner[2])
    assert response.status_code == 204, response.text
    assert response.content == b""
    assert await db_session.scalar(
        select(func.count()).select_from(Agent).where(Agent.id == agent_id)
    ) == 0
    assert (await client.get(f"/agents/{agent_id}", headers=owner[2])).status_code == 404
    assert (await heartbeat(client, token)).status_code == 401
    assert (await client.delete(f"/agents/{agent_id}", headers=owner[2])).status_code == 404


@pytest.mark.parametrize("foreign", [False, True], ids=["missing", "other-owner"])
async def test_delete_unowned_agent_preserves_registration(
    client, db_session, owner_factory, created_agent, foreign
):
    agent, token = created_agent
    _, _, other_headers = await owner_factory()
    target = agent.id if foreign else uuid4()
    response = await client.delete(f"/agents/{target}", headers=other_headers)
    assert response.status_code == 404
    await db_session.refresh(agent)
    assert agent.status == AgentStatus.PENDING
    assert (await heartbeat(client, token)).status_code == 200


@pytest.mark.parametrize("credential", ["missing", "agent-token"])
async def test_delete_requires_user_jwt(client, db_session, created_agent, credential):
    agent, token = created_agent
    headers = {} if credential == "missing" else bearer(token)
    response = await client.delete(f"/agents/{agent.id}", headers=headers)
    assert response.status_code == 401
    await db_session.refresh(agent)
    assert agent.status == AgentStatus.PENDING


async def test_delete_preserves_server_history_and_other_agent(
    client, db_session, owner, owner_factory, created_agent
):
    agent, _ = created_agent
    server = owner[1]
    metric = Metric(
        server_id=server.id, cpu_usage=10, memory_usage=20, disk_usage=30,
        network_in_bytes=123, network_out_bytes=456, process_count=1,
        uptime_seconds=100,
    )
    alert = Alert(
        server_id=server.id, severity=AlertSeverity.WARNING,
        metric_name="cpu_usage", metric_value=90, threshold=80, title="CPU elevada",
    )
    db_session.add_all([metric, alert])
    await db_session.flush()
    _, other_server, other_headers = await owner_factory()
    other_response = await client.post(f"/servers/{other_server.id}/agent", headers=other_headers)
    assert other_response.status_code == 201
    other_id = UUID(other_response.json()["id"])

    response = await client.delete(f"/agents/{agent.id}", headers=owner[2])
    assert response.status_code == 204
    # refresh consulta o banco, sem depender dos objetos ainda no identity map.
    for record in (server, metric, alert):
        await db_session.refresh(record)
    assert server.customer_id is not None
    assert metric.server_id == server.id and metric.network_in_bytes == 123
    assert alert.server_id == server.id and alert.metric_value == 90
    assert (await client.get(f"/agents/{other_id}", headers=other_headers)).status_code == 200
    assert (await heartbeat(client, other_response.json()["token"])).status_code == 200


async def test_recreate_agent_issues_new_credential_and_rejects_old_token(
    client, db_session, owner, created_agent
):
    old_agent, old_token = created_agent
    old_id, old_hash = old_agent.id, old_agent.token_hash
    assert (await client.delete(f"/agents/{old_id}", headers=owner[2])).status_code == 204
    response = await client.post(f"/servers/{owner[1].id}/agent", headers=owner[2])
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"] != str(old_id)
    assert body["token"] != old_token
    assert body["status"] == "PENDING"
    assert body["last_seen_at"] is None
    new_agent = await db_session.get(Agent, UUID(body["id"]))
    assert new_agent.token_hash != old_hash
    assert (await heartbeat(client, old_token)).status_code == 401
    assert (await heartbeat(client, body["token"])).status_code == 200
    assert await db_session.scalar(
        select(func.count()).select_from(Agent).where(Agent.server_id == owner[1].id)
    ) == 1


@pytest_asyncio.fixture
async def committed_server(db_session):
    """Dados visíveis entre conexões, separados das fixtures sem commit externo."""
    engine = db_session.bind.engine
    user_id, customer_id, server_id = uuid4(), uuid4(), uuid4()
    async with AsyncSession(engine, expire_on_commit=False) as session:
        session.add(User(id=user_id, name="Concorrência Agent", email=f"{user_id}@example.com",
                         password_hash=DUMMY_PASSWORD_HASH, role=UserRole.ADMIN))
        await session.flush()
        session.add(Customer(id=customer_id, user_id=user_id, name="Concorrência"))
        await session.flush()
        session.add(Server(id=server_id, customer_id=customer_id, name="Concorrência"))
        await session.commit()
    try:
        yield engine, user_id, server_id
    finally:
        async with AsyncSession(engine) as session:
            # Customer exclui seus Servers/Agents por cascata.
            await session.execute(delete(Customer).where(Customer.id == customer_id))
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()


async def test_concurrent_creation_allows_only_one_agent(committed_server):
    engine, user_id, server_id = committed_server
    both_checked = asyncio.Event()
    checked = 0

    class BarrierRepository(AgentRepository):
        async def get_by_server_id(self, target):
            nonlocal checked
            result = await super().get_by_server_id(target)
            assert result is None
            checked += 1
            if checked == 2:
                both_checked.set()
            await both_checked.wait()
            return result

    async def create():
        async with AsyncSession(engine, expire_on_commit=False) as session:
            service = AgentService(BarrierRepository(session), ServerRepository(session))
            user = await session.get(User, user_id)
            try:
                agent, token = await service.create(server_id, user)
                await session.commit()
                return "created", agent.id, token
            except ConflictError:
                await session.rollback()
                return "conflict", None, None

    results = await asyncio.wait_for(asyncio.gather(create(), create()), timeout=15)
    assert sorted(result[0] for result in results) == ["conflict", "created"]
    async with AsyncSession(engine) as session:
        agents = (await session.scalars(select(Agent).where(Agent.server_id == server_id))).all()
        assert len(agents) == 1
        winner = next(result for result in results if result[0] == "created")
        assert agents[0].id == winner[1]
        assert verify_agent_secret(parse_agent_token(winner[2])[1], agents[0].token_hash)


@pytest.mark.parametrize("change", ["disable", "credential-change", "delete"])
async def test_heartbeat_rechecks_database_after_authentication(committed_server, change):
    engine, user_id, server_id = committed_server
    agent_id = uuid4()
    token, digest = generate_agent_token(agent_id)
    async with AsyncSession(engine) as session:
        session.add(Agent(id=agent_id, server_id=server_id, token_hash=digest))
        await session.commit()

    authenticated, resume = asyncio.Event(), asyncio.Event()

    class PausedRepository(AgentRepository):
        async def record_heartbeat(self, **kwargs):
            authenticated.set()
            await resume.wait()
            return await super().record_heartbeat(**kwargs)

    async def send_heartbeat():
        async with AsyncSession(engine, expire_on_commit=False) as session:
            service = AgentService(PausedRepository(session), ServerRepository(session))
            with pytest.raises(UnauthorizedError):
                await service.heartbeat(token, AgentHeartbeat(version="9.0.0"))
            await session.rollback()

    task = asyncio.create_task(send_heartbeat())
    try:
        await asyncio.wait_for(authenticated.wait(), timeout=10)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            if change == "disable":
                service = AgentService(AgentRepository(session), ServerRepository(session))
                await service.disable(agent_id, await session.get(User, user_id))
            elif change == "delete":
                service = AgentService(AgentRepository(session), ServerRepository(session))
                await service.delete(agent_id, await session.get(User, user_id))
            else:
                await session.execute(update(Agent).where(Agent.id == agent_id)
                                      .values(token_hash=generate_agent_token(agent_id)[1]))
            await session.commit()
        resume.set()
        await asyncio.wait_for(task, timeout=10)
    finally:
        resume.set()
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async with AsyncSession(engine) as session:
        agent = await session.get(Agent, agent_id)
        if change == "delete":
            assert agent is None
            return
        assert agent.status == (AgentStatus.DISABLED if change == "disable" else AgentStatus.PENDING)
        assert agent.last_seen_at is None
        assert agent.version == "1.0.0"
