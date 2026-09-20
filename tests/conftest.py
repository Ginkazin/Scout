from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import test_settings
from app.core.database import get_db
from app.models import Base
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.agent import Agent
from app.models.alert import Alert
from app.models.customer import Customer
from app.models.metric import Metric
from app.models.plan import Plan
from app.models.server import Server
from app.models.subscription import Subscription
from app.models.user import User


if not test_settings.DATABASE_URL_TEST:
    raise RuntimeError("DATABASE_URL_TEST não esta configurada.")

test_engine = create_async_engine(
    test_settings.DATABASE_URL_TEST.get_secret_value(),
    pool_pre_ping=True,
)

TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

@pytest_asyncio.fixture(scope="function", autouse=True)
async def prepare_database():
    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)   

    yield

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture()
async def db_session():
    async with test_engine.connect() as connection:
        transaction = await connection.begin()

        session = TestSessionLocal(bind=connection)

        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()

@pytest_asyncio.fixture()
async def client (db_session, AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db    

    transport = ASGITransport(app=app)             

    async with AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client

    app.dependency_overrides.clear()
