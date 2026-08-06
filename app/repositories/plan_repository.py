from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.plan import Plan
from app.repositories.base_repository import BaseRepository

# Repositório específico para a entidade Plan, fornecendo métodos adicionais além dos métodos genéricos do BaseRepository.
class PlanRepository(BaseRepository[Plan]):
    def __init__(self, db: AsyncSession):
        super().__init__(Plan, db)

    # Método para buscar um plano ativo pelo seu nome. Retorna None se não encontrado.
    async def get_active_by_name(self, name: str) -> Plan | None:
        result = await self.db.execute(
            select(Plan).where(
                Plan.name == name,
                Plan.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    # Método para listar todos os planos ativos. Retorna uma lista de objetos Plan.
    async def list_active(self) -> list[Plan]:
        result = await self.db.execute(
            select(Plan).where(Plan.is_active.is_(True))
        )
        return list(result.scalars().all())