import hashlib
import secrets


INSTALLATION_CODE_PREFIX = "scout_install_"
INSTALLATION_SECRET_LENGTH = 43

INSTALLATION_SECRET_CHARACTERS = frozenset(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789-_"
)

# Valida o formato do código de instalação e retorna o hash do código completo.
def hash_installation_code(code: str) -> str:
    """Valida o formato e retorna o hash do código completo."""
    expected_length = (
        len(INSTALLATION_CODE_PREFIX)
        + INSTALLATION_SECRET_LENGTH
    )

    if (
        len(code) != expected_length
        or not code.startswith(INSTALLATION_CODE_PREFIX)
    ):
        raise ValueError("Código de instalação inválido")

    secret = code[len(INSTALLATION_CODE_PREFIX):]

    if any(
        character not in INSTALLATION_SECRET_CHARACTERS
        for character in secret
    ):
        raise ValueError("Código de instalação inválido")

    return hashlib.sha256(code.encode("ascii")).hexdigest()

#Retorna o código original e seu hash para armazenamento.
def generate_installation_code() -> tuple[str, str]:
    secret = secrets.token_urlsafe(32)
    code = f"{INSTALLATION_CODE_PREFIX}{secret}"

    return code, hash_installation_code(code)