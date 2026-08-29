from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from sqlalchemy import text
from app.api.v1.router.auth_router import router as auth_router
from app.api.v1.router.customer_router import router as customer_router
from app.core.database import engine
from app.core.scheduler import start_scheduler, stop_scheduler

# Configuração do logger
logger = logging.getLogger(__name__)

# Configuração do ciclo de vida da aplicação
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

        logger.info(
            "Conexão com o banco de dados estabelecida com sucesso."
        )

        start_scheduler()

        yield

    except Exception:
        logger.exception(
            "Erro durante ciclo de vida da aplicação."
        )
        raise

    finally:
        stop_scheduler()
        await engine.dispose()

        logger.info(
            "Recursos da aplicação encerrados."
        )

# Inicialização da aplicação FastAPI
app = FastAPI(lifespan=lifespan)

# Inclusão dos routers da aplicação
app.include_router(auth_router)
app.include_router(customer_router)