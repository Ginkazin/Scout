import logging

from app.core.config import settings
from app.core.database import SessionLocal
from app.repositories.agent_repository import AgentRepository


logger = logging.getLogger(__name__)

# Função para verificar agentes offline e marcar aqueles que não enviaram heartbeat dentro do tempo limite configurado.
async def check_offline_agents() -> int:
    async with SessionLocal.begin() as session:
        repository = AgentRepository(session)

        affected = await repository.mark_stale_agents_offline(
            timeout_seconds=settings.AGENT_OFFLINE_TIMEOUT_SECONDS,
        )

    if affected:
        logger.info(
            "%s agente(s) marcado(s) como OFFLINE por ausência de heartbeat.",
            affected,
        )

    return affected