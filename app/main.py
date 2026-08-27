from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
import logging
from app.core.database import engine
from app.core.scheduler import start_scheduler, stop_scheduler
from app.api.v1.router.auth_router import router as auth_router
from app.api.v1.router.customer_router import router as customer_router

logger = logging.getLogger(__name__)

# Configuração do lifespan da aplicação FastAPI para gerenciar a conexão com o banco de dados
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Executa ao iniciar a aplicação
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

        logger.info(
            "Conexão com o banco de dados estabelecida com sucesso."
        )

        start_scheduler() # Inicia o agendador de tarefas

        yield

    except Exception:
        logger.exception(
            "Erro durante ciclo de vida da aplicação."
        )
        raise #impede a aplicação de subir se o banco estiver inacessível

    finally:
        stop_scheduler() # Encerra o agendador de tarefas
        await engine.dispose
        logger.info("Recursos da aplicação encerrados.")

# Inicializa a aplicação FastAPI com o lifespan configurado
app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)
app.include_router(customer_router)