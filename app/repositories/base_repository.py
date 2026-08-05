from typing import Generic, TypeVar
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.base import BaseModel


ModelType = TypeVar("ModelType", bound=BaseModel)

# Repositório genérico que fornece operações CRUD básicas para qualquer modelo de banco de dados que herde de BaseModel.
class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    # Método para buscar um registro pelo seu ID. Retorna None se não encontrado.
    async def get_by_id(self, obj_id: UUID) -> ModelType | None:
        return await self.db.get(self.model, obj_id)

    # Método para listar todos os registros do modelo, com suporte a paginação através dos parâmetros skip e limit.
    async def list_all(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        result = await self.db.execute(
            select(self.model).offset(skip).limit(limit)
        )

        return list(result.scalars().all())

    # Método para criar um novo registro no banco de dados. Adiciona o objeto à sessão, faz flush e refresh para garantir que o objeto esteja atualizado com os valores do banco.
    async def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)

        return obj

    # Método para atualizar um registro existente no banco de dados. Faz flush e refresh para garantir que o objeto esteja atualizado com os valores do banco.
    async def update(self, obj: ModelType) -> ModelType:
        await self.db.flush()
        await self.db.refresh(obj)

        return obj

    # Método para deletar um registro do banco de dados. Faz flush para aplicar a exclusão.
    async def delete(self, obj: ModelType,) -> None:
        await self.db.delete(obj)
        await self.db.flush()