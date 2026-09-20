import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from app.core.config import test_settings
from app.core.database import get_db
from app.main import app
from app.models.base import Base
from decimal import Decimal
from app.models.plan import Plan
from app.models.agent import Agent
from app.models.alert import Alert
from app.models.customer import Customer
from app.models.metric import Metric
from app.models.plan import Plan
from app.models.server import Server
from app.models.subscription import Subscription
from app.models.user import User


if test_settings.DB_TEST_NAME != "scout_test":
    raise RuntimeError(
        "Os testes só podem ser executados no banco scout_test."
    )


test_engine = create_async_engine(
    test_settings.DATABASE_URL_TEST.get_secret_value(),
    poolclass=NullPool,
    connect_args={
        "ssl": False,
    },
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database():
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session():
    async with test_engine.connect() as connection:
        transaction = await connection.begin()

        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as test_client:
        yield test_client

    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def free_plan(db_session: AsyncSession) -> Plan:
    plan = Plan(
        name="FREE",
        price=Decimal("0.00"),
        max_customers=1,
        max_servers=3,
        max_users=1,
        retention_days=30,
        agent_auto_update=True,
        is_active=True,
    )

    db_session.add(plan)
    await db_session.flush()
    await db_session.refresh(plan)

    return plan