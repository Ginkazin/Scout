from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer()

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Não foi possível validar as credenciais",
    headers={"WWW-Authenticate": "Bearer"},
)

# Dependency para obter o usuário atual a partir do token de acesso
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        subject = payload.get("sub")
        if subject is None:
            raise credentials_exception
        user_id = UUID(subject)
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise credentials_exception from exc

    user_repository = UserRepository(db)
    user = await user_repository.get_by_id(user_id)

    if user is None or not user.is_active:
        raise credentials_exception

    return user

#Factory de dependency para restringir rotas por papel do usuário. Uso: Depends(require_role(UserRole.ADMIN))
def require_role(*allowed_roles: UserRole):

    async def _check_role(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para executar esta ação",
            )
        return current_user

    return _check_role