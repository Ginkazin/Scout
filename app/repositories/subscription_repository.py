from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.subscription import Subscription, SubscriptionStatus
from app.repositories.base_repository import BaseRepository

#class SubscriptionRepository é responsável por gerenciar as operações de banco de dados relacionadas à tabela de assinaturas.
class SubscriptionRepository(BaseRepository[Subscription]):
    def __init__(self, db: AsyncSession):
        super().__init__(Subscription, db)

    #get_by_user_id busca uma assinatura específica com base no ID do usuário.
    async def get_by_user_id(self, user_id: UUID) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    #list_by_status busca todas as assinaturas com um status específico.
    async def list_by_status(self, status: SubscriptionStatus) -> list[Subscription]:
        result = await self.db.execute(
            select(Subscription).where(Subscription.status == status)
        )
        return list(result.scalars().all())

    #count_by_plan_id conta o número de assinaturas associadas a um ID de plano específico.
    async def count_by_plan_id(self, plan_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Subscription).where(Subscription.plan_id == plan_id)
        )
        return result.scalar_one()

    # get_by_user_id_for_update busca uma assinatura específica com base no ID do usuário e bloqueia a linha para atualização, garantindo que nenhuma outra transação possa modificar essa assinatura até que a transação atual seja concluída.
    async def get_by_user_id_for_update(self, user_id: UUID) -> Subscription | None:
        result = await self.db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()