from http.client import HTTPException
import json
import logging
import platform
import time
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPRedirectHandler,
    Request,
    build_opener,
)
from config import load_configuration


AGENT_VERSION = "1.0.0"
HEARTBEAT_INTERVAL_SECONDS = 60
REQUEST_TIMEOUT_SECONDS = 10

logger = logging.getLogger("scout.agent")


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Não encaminha a credencial para outro endereço.
        return None

def send_heartbeat(opener, api_url: str, token: str) -> bool:
    payload = json.dumps(
        {"version": AGENT_VERSION}
    ).encode("utf-8")

    request = Request(
        url=f"{api_url}/agent/heartbeat",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    try:
        with opener.open(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:
            if response.status != 200:
                logger.warning(
                    "Resposta inesperada no heartbeat: HTTP %s.",
                    response.status,
                )
                return False

    except HTTPError as exc:
        try:
            if exc.code == 401:
                logger.warning(
                    "Heartbeat recusado: confira o token e "
                    "se o Agent está habilitado."
                )
            else:
                logger.warning(
                    "Heartbeat recusado pela API: HTTP %s.",
                    exc.code,
                )
        finally:
            exc.close()

        return False

    except (URLError, TimeoutError, OSError, HTTPException):
        logger.warning(
            "Não foi possível comunicar com a API. "
            "Uma nova tentativa será feita no próximo ciclo."
        )
        return False

    logger.info("Heartbeat aceito pela API.")
    return True

def fetch_runtime_config(
    opener,
    api_url: str,
    token: str,
) -> dict | None:
    request = Request(
        url=f"{api_url}/agent/config",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with opener.open(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS,
        ) as response:
            if response.status != 200:
                logger.warning(
                    "Resposta inesperada ao consultar configuração: HTTP %s.",
                    response.status,
                )
                return None

            max_response_bytes = 64 * 1024
            body = response.read(max_response_bytes + 1)

            if len(body) > max_response_bytes:
                logger.error("Resposta de configuração excedeu o tamanho permitido.")
                return None

            configuration = json.loads(body.decode("utf-8"))

    except HTTPError as exc:
        try:
            if exc.code == 401:
                logger.warning(
                    "Configuração recusada: confira o token "
                    "e se o Agent está habilitado."
                )
            elif exc.code == 409:
                logger.warning(
                    "Configuração incompleta. Confira o cadastro "
                    "do servidor no Scout."
                )
            else:
                logger.warning(
                    "Falha ao consultar configuração: HTTP %s.",
                    exc.code,
                )
        finally:
            exc.close()

        return None

    except (URLError, TimeoutError, OSError, HTTPException):
        logger.warning(
            "Não foi possível consultar a configuração. "
            "Nova tentativa no próximo ciclo."
        )
        return None

    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.error("A API retornou uma configuração com formato inválido.")
        return None

    if not isinstance(configuration, dict):
        logger.error("A configuração recebida deve ser um objeto JSON.")
        return None

    if configuration.get("agent_type") not in (
        "INFRASTRUCTURE",
        "DATABASE",
    ):
        logger.error("A API retornou um tipo de Agent não suportado.")
        return None

    if configuration.get("server_os_family") not in (
        "WINDOWS",
        "LINUX",
    ):
        logger.error("A API retornou um sistema operacional não suportado.")
        return None

    return configuration

def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    try:
        api_url, token = load_configuration()
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    local_os = platform.system().upper()

    if local_os not in ("WINDOWS", "LINUX"):
        logger.error(
            "Sistema operacional não suportado: %s.",
            local_os,
        )
        return 1

    opener = build_opener(NoRedirectHandler())
    previous_configuration = None

    logger.info(
        "Scout Agent %s iniciado em %s.",
        AGENT_VERSION,
        local_os,
    )

    try:
        while True:
            cycle_start = time.monotonic()

            configuration = fetch_runtime_config(
                opener,
                api_url,
                token,
            )

            if configuration is not None:
                expected_os = configuration["server_os_family"]
                agent_type = configuration["agent_type"]

                if expected_os != local_os:
                    logger.error(
                        "Sistema incompatível: cadastro=%s, máquina=%s. "
                        "Confira o token e o servidor selecionado no Scout.",
                        expected_os,
                        local_os,
                    )
                else:
                    configuration_key = (
                        agent_type,
                        expected_os,
                    )

                    if configuration_key != previous_configuration:
                        logger.info(
                            "Configuração validada: tipo=%s, sistema=%s.",
                            agent_type,
                            expected_os,
                        )
                        previous_configuration = configuration_key

                    send_heartbeat(opener, api_url, token)

            elapsed = time.monotonic() - cycle_start
            remaining = max(
                0,
                HEARTBEAT_INTERVAL_SECONDS - elapsed,
            )

            time.sleep(remaining)

    except KeyboardInterrupt:
        logger.info("Scout Agent encerrado.")
        return 0

if __name__ == "__main__":
    raise SystemExit(main())