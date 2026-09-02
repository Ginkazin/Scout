from uuid import UUID
from sqlalchemy.exc import IntegrityError
from app.models.customer import Customer
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.schemas.customer_schema import CustomerCreate, CustomerUpdate

# Classe de serviço para gerenciar operações relacionadas a clientes.
class CustomerService:
    def __init__(self, customer_repository: CustomerRepository, plan_repository: PlanRepository, subscription_repository: SubscriptionRepository):
        self.customer_repository = customer_repository
        self.plan_repository = plan_repository
        self.subscription_repository = subscription_repository

# função privada para verificar se o usuário atual atingiu o limite de clientes permitido pelo seu plano.
    async def _check_customer_limit(self, current_user: User) -> None:
        subscription = await self.subscription_repository.get_by_user_id(current_user.id)
        if subscription is None:
            raise ValueError("Usuário sem assinatura ativa.")

        plan = await self.plan_repository.get_by_id(subscription.plan_id)
        if plan is None:
            raise ValueError("Plano da assinatura não encontrado.")

        current_count = await self.customer_repository.count_by_user_id(current_user.id)
        if current_count >= plan.max_customers:
            raise ValueError(
                f"Limite de clientes do plano '{plan.name}' atingido. "
                f"({plan.max_customers}). Faça upgrade para adicionar mais. "
            )

# Método para criar um novo cliente.
    async def create(
            self,
            data: CustomerCreate,
            current_user: User,
    ) -> Customer:
        existing_customer = await self.customer_repository.get_by_name_and_user_id(
            name=data.name,
            user_id=current_user.id,
        )

        if existing_customer is not None:
            raise ValueError("Já existe um cliente com esse nome")

        await self._check_customer_limit(current_user)

        customer = Customer(
            user_id=current_user.id,
            name=data.name,
            company=data.company,
            email=str(data.email) if data.email is not None else None,
            phone=data.phone,
            notes=data.notes,
        )

        try:
            return await self.customer_repository.create(customer)
        except IntegrityError as exc:
            raise ValueError("Já existe um cliente com esse nome") from exc

# Método para obter um cliente pelo ID e pelo usuário atual.
    async def get_by_id(
            self,
            customer_id: UUID,
            current_user: User,
    ) -> Customer:
        customer = await self.customer_repository.get_by_id_and_user_id(
            customer_id=customer_id,
            user_id=current_user.id,
        )

        if customer is None:
            raise ValueError("Cliente não encontrado")

        return customer

# Método para listar clientes do usuário atual com paginação.
    async def list(
            self,
            current_user:User,
            skip:int = 0,
            limit:int = 100,
    ) -> list[Customer]:
        return await self.customer_repository.list_by_user_id(
            user_id=current_user.id,
            skip=skip,
            limit=limit,
        )

# Método para atualizar um cliente existente.
    async def update(
            self,
            customer_id:UUID,
            data:CustomerUpdate,
            current_user:User,
    ) -> Customer:
        customer = await self.get_by_id(
            customer_id=customer_id,
            current_user=current_user
        )

        update_data = data.model_dump(exclude_unset=True)

        if "name" in update_data:
            existing_customer = await self.customer_repository.get_by_name_and_user_id(
                name=update_data["name"],
                user_id=current_user.id,
            )

            if(
                existing_customer is not None
                and existing_customer.id != customer.id
            ):
                raise ValueError("Já existe um cliente com esse nome")

        for field, value in update_data.items():
            setattr(customer, field, value)

        try:    
            return await self.customer_repository.update(customer)
        except IntegrityError as exc:
            raise ValueError("Já existe um cliente com esse nome") from exc

# Método para deletar um cliente existente.
    async def delete(
            self,
            customer_id:UUID,
            current_user: User,
    ) -> None:
        customer = await self.get_by_id(
            customer_id=customer_id,
            current_user=current_user,
        )

        await self.customer_repository.delete(customer)
