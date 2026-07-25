from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# Cria o engine de conexão com o banco de dados PostgreSQL usando asyncpg e SQLAlchemy
engine = create_async_engine(
    settings.DATABASE_URL.get_secret_value(),
    pool_pre_ping=True,
    echo=False,
)

# Cria a fábrica de sessões assíncronas para interagir com o banco de dados
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Context manager para obter uma sessão de banco de dados assíncrona
async def get_db():
    async with SessionLocal() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise