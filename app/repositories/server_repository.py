from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.customer import Customer
from app.models.server import Server
from app.repositories.base_repository import BaseRepository

# classe de repositório para gerenciar operações relacionadas a servidores
class ServerRepository(BaseRepository[Server]):
    def __init__(self, db: AsyncSession):
        super().__init__(Server, db)

    # método para obter um servidor específico pelo ID e pelo ID do usuário, garantindo que o servidor pertença ao usuário
    async def get_by_id_and_user_id(
        self,
        server_id: UUID,
        user_id: UUID,
    ) -> Server | None:
        result = await self.db.execute(
            select(Server)
            .join(
                Customer,
                Server.customer_id == Customer.id,
            )
            .where(
                Server.id == server_id,
                Customer.user_id == user_id,
            )
        )

        return result.scalar_one_or_none()

    # método para listar todos os servidores de um cliente específico, garantindo que o cliente pertença ao usuário
    async def list_by_customer_id_and_user_id(
        self,
        customer_id: UUID,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Server]:
        result = await self.db.execute(
            select(Server)
            .join(
                Customer,
                Server.customer_id == Customer.id,
            )
            .where(
                Server.customer_id == customer_id,
                Customer.user_id == user_id,
            )
            .order_by(Server.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        return list(result.scalars().all())

    # método para obter um servidor específico pelo nome e pelo ID do cliente, garantindo que o servidor pertença ao cliente
    async def get_by_name_and_customer_id(
        self,
        name: str,
        customer_id: UUID,
    ) -> Server | None:
        result = await self.db.execute(
            select(Server).where(
                Server.customer_id == customer_id,
                Server.name == name,
            )
        )

        return result.scalar_one_or_none()

    # método para deletar um servidor específico
    async def count_by_user_id(
        self,
        user_id: UUID,
    ) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(Server)
            .join(
                Customer,
                Server.customer_id == Customer.id,
            )
            .where(
                Customer.user_id == user_id
            )
        )

        return result.scalar_one()