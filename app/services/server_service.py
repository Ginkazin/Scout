from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ConflictError, NotFoundError, PlanLimitExceededError
from app.models.server import Server
from app.models.user import User
from app.models.subscription import SubscriptionStatus
from app.repositories.customer_repository import CustomerRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.server_repository import ServerRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.server_schema import ServerCreate, ServerUpdate


class ServerService:
    def __init__(
        self,
        server_repository: ServerRepository,
        customer_repository: CustomerRepository,
        subscription_repository: SubscriptionRepository,
        plan_repository: PlanRepository,
    ):
        self.server_repository = server_repository
        self.customer_repository = customer_repository
        self.subscription_repository = subscription_repository
        self.plan_repository = plan_repository

    async def _get_owned_customer(self, customer_id: UUID, current_user: User):
        customer = await self.customer_repository.get_by_id_and_user_id(
            customer_id=customer_id, user_id=current_user.id
        )
        if customer is None:
            raise NotFoundError("Cliente não encontrado")
        return customer

    async def _check_server_limit(self, current_user: User) -> None:
        subscription = await self.subscription_repository.get_by_user_id(current_user.id)
        if subscription is None:
            raise NotFoundError("Assinatura do usuário não encontrada")
        if subscription.status not in [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]:
            raise PlanLimitExceededError(
                "Assinatura do usuário não está ativa. Não é possível adicionar servidores."
            )

        plan = await self.plan_repository.get_by_id(subscription.plan_id)
        if plan is None:
            raise NotFoundError("Plano da assinatura não encontrado")

        current_count = await self.server_repository.count_by_user_id(current_user.id)
        if current_count >= plan.max_servers:
            raise PlanLimitExceededError(
                f"Limite de servidores do plano '{plan.name}' atingido "
                f"(máximo de {plan.max_servers}). Faça upgrade para adicionar mais."
            )

    async def create(self, customer_id: UUID, data: ServerCreate, current_user: User) -> Server:
        await self._get_owned_customer(customer_id, current_user)

        existing = await self.server_repository.get_by_name_and_customer_id(
            name=data.name, customer_id=customer_id
        )
        if existing is not None:
            raise ConflictError("Já existe um servidor com esse nome para esse cliente")

        await self._check_server_limit(current_user)

        server = Server(
            customer_id=customer_id,
            name=data.name,
            server_type=data.server_type,
            hostname=data.hostname,
            ip_address=str(data.ip_address) if data.ip_address is not None else None,
            operating_system=data.operating_system,
            description=data.description,
        )

        try:
            return await self.server_repository.create(server)
        except IntegrityError as exc:
            raise ConflictError("Já existe um servidor com esse nome para esse cliente") from exc

    async def get_by_id(self, server_id: UUID, current_user: User) -> Server:
        server = await self.server_repository.get_by_id_and_user_id(
            server_id=server_id, user_id=current_user.id
        )
        if server is None:
            raise NotFoundError("Servidor não encontrado")
        return server

    async def list_by_customer(
        self,
        customer_id: UUID,
        current_user: User,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Server]:
        await self._get_owned_customer(customer_id, current_user)
        return await self.server_repository.list_by_customer_id_and_user_id(
            customer_id=customer_id, user_id=current_user.id, skip=skip, limit=limit
        )

    async def update(self, server_id: UUID, data: ServerUpdate, current_user: User) -> Server:
        server = await self.get_by_id(server_id, current_user)
        update_data = data.model_dump(exclude_unset=True)

        if "name" in update_data:
            existing = await self.server_repository.get_by_name_and_customer_id(
                name=update_data["name"], customer_id=server.customer_id
            )
            if existing is not None and existing.id != server.id:
                raise ConflictError("Já existe um servidor com esse nome para esse cliente")

        if "ip_address" in update_data and update_data["ip_address"] is not None:
            update_data["ip_address"] = str(update_data["ip_address"])

        for field, value in update_data.items():
            setattr(server, field, value)

        try:
            return await self.server_repository.update(server)
        except IntegrityError as exc:
            raise ConflictError("Já existe um servidor com esse nome para esse cliente") from exc

    async def delete(self, server_id: UUID, current_user: User) -> None:
        server = await self.get_by_id(server_id, current_user)
        await self.server_repository.delete(server)