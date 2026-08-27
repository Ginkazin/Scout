from uuid import UUID
from sqlalchemy.exc import IntegrityError
from app.models.customer import Customer
from app.models.user import User
from app.repositories.customer_repository import CustomerRepository
from app.schemas.customer_schema import CustomerCreate, CustomerUpdate

class CustomerService:
    def __init__(self, customer_repository: CustomerRepository):
        self.customer_repository = customer_repository

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

    async def get_by_id(
            self,
            customer_id=UUID,
            current_user=User,
    ) -> Customer:
        customer = await self.customer_repository.get_by_id_and_user_id(
            customer_id=customer_id,
            user_id=current_user.id,
        )

        if customer is None:
            raise ValueError("Cliente não encontrado")

        return customer

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
