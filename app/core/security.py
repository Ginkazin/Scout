from datetime import datetime, timedelta, timezone
from uuid import UUID
import jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Função para validar a força da senha
def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres.")
    if not any(char.isdigit() for char in password):
        raise ValueError("A senha deve conter pelo menos um número.")
    if not any(char.isupper() for char in password):
        raise ValueError("A senha deve conter pelo menos uma letra maiúscula.")
    if not any(char.islower() for char in password):
        raise ValueError("A senha deve conter pelo menos uma letra minúscula.")
    if not any(char in "!@#$%^&*()-_=+[]{}|;:'\",.<>?/`~" for char in password):
        raise ValueError("A senha deve conter pelo menos um caractere especial.")
    return password

# Funções para hash e verificação de senhas
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Verifica se a senha fornecida corresponde à senha armazenada (hash)
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Funções para criação e decodificação de tokens JWT
def _create_token_jwt(subject: UUID, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(
        payload,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.ALGORITHM,
    )

# Cria um token de acesso
def create_access_token(user_id: UUID) -> str:
    return _create_token_jwt(
        subject=user_id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )

# Cria um token de refresh
def create_refresh_token(user_id: UUID) -> str:
    return _create_token_jwt(
        subject=user_id,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )

# Decodifica um token JWT
def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        settings.SECRET_KEY.get_secret_value(),
        algorithms=[settings.ALGORITHM],
    )