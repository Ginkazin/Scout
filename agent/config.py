import os
from pathlib import Path
import tomllib
from urllib.parse import urlsplit


def read_text_file(path: Path, limit: int, description: str) -> str:
    try:
        with path.open("rb") as file:
            content = file.read(limit + 1)
    except OSError:
        raise ValueError(
            f"Não foi possível ler {description}."
        ) from None

    if len(content) > limit:
        raise ValueError(f"{description} excede o tamanho permitido.")

    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        raise ValueError(
            f"{description} precisa usar a codificação UTF-8."
        ) from None


def validate_api_url(value: str) -> str:
    api_url = value.strip().rstrip("/")

    if not api_url:
        raise ValueError("Configure o endereço da API.")

    if any(character.isspace() for character in api_url):
        raise ValueError("O endereço da API não pode conter espaços.")

    try:
        parsed = urlsplit(api_url)
        port = parsed.port
        hostname = parsed.hostname
    except ValueError:
        raise ValueError("O endereço da API é inválido.") from None

    if (
        not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or (port is not None and port == 0)
    ):
        raise ValueError("O endereço da API é inválido.")

    local_http = (
        parsed.scheme == "http"
        and hostname in {"localhost", "127.0.0.1", "::1"}
    )

    if parsed.scheme != "https" and not local_http:
        raise ValueError(
            "Use HTTPS para uma API remota. "
            "HTTP é permitido apenas em localhost."
        )

    return api_url


def validate_token(value: str) -> str:
    token = value.strip()

    if not token:
        raise ValueError("Configure o token do Agent.")

    if (
        len(token) > 4096
        or not token.isascii()
        or any(not 33 <= ord(character) <= 126 for character in token)
    ):
        raise ValueError("O token do Agent possui formato inválido.")

    return token


def load_configuration() -> tuple[str, str]:
    config_file = os.getenv("SCOUT_CONFIG_FILE")

    if config_file is None:
        # Desenvolvimento: usa somente o ambiente do processo.
        api_url = os.getenv("SCOUT_API_URL", "")
        token = os.getenv("SCOUT_AGENT_TOKEN", "")

        return validate_api_url(api_url), validate_token(token)

    if not config_file.strip():
        raise ValueError("SCOUT_CONFIG_FILE não pode estar vazio.")

    config_path = Path(config_file)

    if not config_path.is_absolute():
        raise ValueError(
            "SCOUT_CONFIG_FILE precisa ser um caminho absoluto."
        )

    content = read_text_file(
        config_path,
        limit=64 * 1024,
        description="o arquivo de configuração",
    )

    try:
        configuration = tomllib.loads(content)
    except tomllib.TOMLDecodeError:
        # Não inclui o conteúdo do arquivo na mensagem de erro.
        raise ValueError(
            "O arquivo de configuração possui TOML inválido."
        ) from None

    api_url = configuration.get("api_url")
    token_file = configuration.get("token_file")

    if not isinstance(api_url, str):
        raise ValueError("Informe api_url como texto na configuração.")

    if not isinstance(token_file, str) or not token_file.strip():
        raise ValueError("Informe token_file na configuração.")

    token_path = Path(token_file)

    if not token_path.is_absolute():
        token_path = config_path.parent / token_path

    token = read_text_file(
        token_path,
        limit=4096,
        description="o arquivo do token",
    )

    return validate_api_url(api_url), validate_token(token)