from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.customer import Customer
from app.repositories.base_repository import BaseRepository

# Repositório para gerenciar operações relacionadas a clientes no banco de dados.
class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, db:AsyncSession):
        super().__init__(Customer, db)

# Método para obter um cliente pelo ID e pelo usuário atual.
    async def get_by_id_and_user_id(
            self,
            customer_id: UUID,
            user_id: UUID,
    ) -> Customer | None:
        result = await self.db.execute(
            select(Customer).where(
                Customer.id == customer_id,
                Customer.user_id == user_id,
            )
        )

        return result.scalar_one_or_none()

#   Método para listar clientes do usuário atual com paginação.
    async def list_by_user_id(
            self,
            user_id: UUID,
            skip: int = 0,
            limit: int = 100,
    ) -> list[Customer]:
        result = await self.db.execute(
            select(Customer)
            .where(Customer.user_id == user_id)
            .order_by(Customer.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        return list(result.scalars().all())

# Método para obter um cliente pelo nome e pelo usuário atual.
    async def get_by_name_and_user_id(
            self,
            name: str,
            user_id: UUID,
    ) -> Customer | None:
        result = await self.db.execute(
            select(Customer).where(
                Customer.user_id == user_id,
                Customer.name == name,
            )
        )

        return result.scalar_one_or_none()

# Método para verificar se um cliente com um nome específico existe para um usuário.
    async def name_exists_for_user(
            self,
            name: str,
            user_id: UUID
    ) -> bool:
        customer = await self.get_by_name_and_user_id(
            name = name,
            user_id= user_id,
        )

        return customer is not None