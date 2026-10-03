from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.server_repository import ServerRepository
from app.services.customer_service import CustomerService
from app.repositories.customer_repository import CustomerRepository
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole
from app.repositories.plan_repository import PlanRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.server_service import ServerService
from app.repositories.agent_repository import AgentRepository
from app.services.agent_service import AgentService

bearer_scheme = HTTPBearer()

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Não foi possível validar as credenciais",
    headers={"WWW-Authenticate": "Bearer"},
)

agent_bearer_scheme = HTTPBearer(
    scheme_name="AgentToken",
    description="Token do agent no formato scout_<agent_id>.<secret>",
    auto_error=False,
)

# Dependency para obter o usuário atual a partir do token de acesso
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db, scope="function"),
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

# Dependency para obter o token do agente a partir do cabeçalho Authorization
def get_agent_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(agent_bearer_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de agente ausente ou invalido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

# Dependency para obter uma instância do AuthService com os repositórios necessários
def get_auth_service(db: AsyncSession = Depends(get_db, scope="function")) -> AuthService:
    return AuthService(
        user_repository=UserRepository(db),
        plan_repository=PlanRepository(db),
        subscription_repository=SubscriptionRepository(db),
    )

# Dependency para obter uma instância do CustomerService com o repositório necessário
def get_customer_service(
        db: AsyncSession = Depends(get_db, scope="function"),
) -> CustomerService:
    return CustomerService(
        customer_repository=CustomerRepository(db),
        plan_repository=PlanRepository(db),
        subscription_repository=SubscriptionRepository(db),
    )

# Dependency para obter uma instância do ServerService com os repositórios necessários    
def get_server_service(db: AsyncSession = Depends(get_db, scope="function")) -> ServerService:
    return ServerService(
        server_repository=ServerRepository(db),
        customer_repository=CustomerRepository(db),
        subscription_repository=SubscriptionRepository(db),
        plan_repository=PlanRepository(db),
    )

# Dependency para obter uma instância do AgentService com os repositórios necessários
def get_agent_service(db: AsyncSession = Depends(get_db, scope="function")) -> AgentService:
    return AgentService(
        agent_repository=AgentRepository(db),
        server_repository=ServerRepository(db),
    )
