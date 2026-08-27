from datetime import datetime, timezone
from uuid import UUID
import jwt
from starlette.concurrency import run_in_threadpool
from sqlalchemy.exc import IntegrityError
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User, UserRole
from app.repositories.plan_repository import PlanRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth_schema import AccessTokenResponse, TokenResponse
from app.schemas.user_schema import UserCreate

DEFAULT_PLAN_NAME = "FREE"


# AuthService é responsável por gerenciar a lógica de autenticação, incluindo registro, login e refresh de tokens.
class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        plan_repository: PlanRepository,
        subscription_repository: SubscriptionRepository,
    ):
        self.user_repository = user_repository
        self.plan_repository = plan_repository
        self.subscription_repository = subscription_repository

    #register é responsável por registrar um novo usuário, criar uma assinatura padrão e retornar o usuário criado.
    async def register(self, data: UserCreate) -> User:
        email = str(data.email).strip().lower()
        if await self.user_repository.email_exists(email):
            raise ValueError("Email já cadastrado")

        default_plan = await self.plan_repository.get_active_by_name(DEFAULT_PLAN_NAME)
        if default_plan is None:
            raise RuntimeError(f"Plano padrão '{DEFAULT_PLAN_NAME}' não configurado")

        password_hash = await run_in_threadpool(hash_password, data.password)

        user = User(
            name=data.name,
            email=email,
            password_hash=password_hash,
            role=UserRole.ADMIN,
        )
        try:
            user = await self.user_repository.create(user)

            subscription = Subscription(
                user_id=user.id,
                plan_id=default_plan.id,
                status=SubscriptionStatus.ACTIVE,
            )

            await self.subscription_repository.create(subscription)

        except IntegrityError as exc:
            raise ValueError("Email já cadastrado") from exc

        return user

    #login é responsável por autenticar um usuário com email e senha, atualizando o último login e retornando tokens de acesso e refresh.
    async def login(self, email: str, password: str) -> dict[str, str]:   
        email = email.strip().lower()
        user = await self.user_repository.get_by_email(email)

        password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
        is_valid = await run_in_threadpool(verify_password, password, password_hash)

        if user is None or not is_valid or not user.is_active:
            raise ValueError("Email ou senha inválidos")

        user.last_login = datetime.now(timezone.utc)
        await self.user_repository.db.flush()

        return{
            "access_token": create_access_token(user.id),
            "refresh_token": create_refresh_token(user.id),
        }

    #refresh é responsável por validar um refresh token, verificar se o usuário ainda está ativo e retornar um novo access token.
    async def refresh(self, refresh_token: str) -> AccessTokenResponse:
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise ValueError("Token inválido")
            subject = payload.get("sub")
            if not subject:
                raise ValueError("Token inválido")
            user_id = UUID(subject)
        except (jwt.PyJWTError, ValueError, TypeError):
            raise ValueError("Token inválido ou expirado")

        user = await self.user_repository.get_by_id(user_id)
        if user is None or not user.is_active:
            raise ValueError("Usuário não encontrado ou inativo")

        return AccessTokenResponse(access_token=create_access_token(user.id))