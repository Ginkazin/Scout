from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.repositories.base_repository import BaseRepository

# Repositório específico para a entidade User, fornecendo métodos adicionais além dos métodos genéricos do BaseRepository.
class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    # Método para buscar um usuário pelo seu email. Retorna None se não encontrado.
    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(User.email == email)
        )

        return result.scalar_one_or_none()

    # Método para verificar se um email já está registrado no banco de dados. Retorna True se existir, caso contrário False.
    async def email_exists(self, email: str) -> bool:
        user = await self.get_by_email(email)
        
        return user is not None