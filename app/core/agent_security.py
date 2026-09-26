import hashlib
import hmac
import secrets
from uuid import UUID

# variáveis e funções para gerar, analisar e verificar tokens de agentes.
TOKEN_PREFIX = "scout_"
SECRET_LENGTH = 43
SECRET_CHARACTERS = frozenset(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789-_"
)

# Função para gerar um hash SHA-256.
def _hash_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("ascii")).hexdigest()

# Função para gerar um token de agente e seu hash correspondente.
def generate_agent_token(agent_id: UUID) -> tuple[str, str]:
    secret = secrets.token_urlsafe(32)

    token = f"{TOKEN_PREFIX}{agent_id}.{secret}"
    token_hash = _hash_secret(secret)

    return token, token_hash

# Função para analisar um token de agente e extrair o ID do agente e o segredo.
def parse_agent_token(token: str) -> tuple[UUID, str]:
    # scout_ + UUID de 36 caracteres + ponto + segredo de 43 caracteres
    expected_length = len(TOKEN_PREFIX) + 36 + 1 + SECRET_LENGTH

    if len(token) != expected_length:
        raise ValueError("Token de agente inválido")

    if not token.startswith(TOKEN_PREFIX):
        raise ValueError("Token de agente inválido")

    agent_id_text, separator, secret = token[len(TOKEN_PREFIX):].partition(".")

    if (
        separator != "."
        or len(secret) != SECRET_LENGTH
        or any(char not in SECRET_CHARACTERS for char in secret)
    ):
        raise ValueError("Token de agente inválido")

    try:
        agent_id = UUID(agent_id_text)
    except ValueError as exc:
        raise ValueError("Token de agente inválido") from exc

    if str(agent_id) != agent_id_text:
        raise ValueError("Token de agente inválido")

    return agent_id, secret

# Função para verificar se um segredo de agente corresponde ao hash armazenado.
def verify_agent_secret(secret: str, stored_hash: str) -> bool:
    if (
        len(secret) != SECRET_LENGTH
        or any(char not in SECRET_CHARACTERS for char in secret)
    ):
        return False

    candidate_hash = _hash_secret(secret)

    return hmac.compare_digest(candidate_hash, stored_hash)