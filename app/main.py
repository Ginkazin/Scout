from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from app.core.database import engine
from app.core.scheduler import start_scheduler, stop_scheduler

# Configuração do lifespan da aplicação FastAPI para gerenciar a conexão com o banco de dados
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Executa ao iniciar a aplicação
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        print("Conexão com o banco de dados estabelecida com sucesso!")
    except Exception as e:
        print(f"Erro ao conectar com o banco de dados: {e}")
        raise  # opcional: impede a aplicação de subir se o banco estiver inacessível

    start_scheduler()  # Inicia o agendador de tarefas

    yield  # a aplicação roda normalmente aqui

    stop_scheduler()  # Encerra o agendador de tarefas

    # Executa ao encerrar a aplicação (cleanup, se precisar)
    await engine.dispose()

# Inicializa a aplicação FastAPI com o lifespan configurado
app = FastAPI(lifespan=lifespan)