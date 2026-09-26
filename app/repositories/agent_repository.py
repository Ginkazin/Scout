from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.agent import Agent
from app.models.customer import Customer
from app.models.server import Server
from app.repositories.base_repository import BaseRepository

# Repositório para gerenciar operações relacionadas a agentes no banco de dados.
class AgentRepository(BaseRepository[Agent]):
    def __init__(self, db: AsyncSession):
        super().__init__(Agent, db)

    # Método para obter um agente pelo ID do servidor.
    async def get_by_server_id(
            self,
            server_id: UUID,
    ) -> Agent | None:
        result = await self.db.execute(
            select(Agent).where(
                Agent.server_id == server_id,
            )
        )

        return result.scalar_one_or_none()

    # Método para obter um agente pelo ID e pelo usuário atual.
    async def get_by_id_and_user_id(
            self,
            agent_id: UUID,
            user_id: UUID,
    ) -> Agent | None:
        result = await self.db.execute(
            select(Agent).join(Server, Agent.server_id == Server.id).join(Customer, Server.customer_id == Customer.id).where(
                Agent.id == agent_id,
                Customer.user_id == user_id
            )
        )

        return result.scalar_one_or_none()