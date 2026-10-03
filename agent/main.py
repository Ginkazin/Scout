import json
import logging
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    Request,
    build_opener,
)


AGENT_VERSION = "1.0.0"
HEARTBEAT_INTERVAL_SECONDS = 60
REQUEST_TIMEOUT_SECONDS = 10

logger = logging.getLogger("scout.agent")


class NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Não encaminha a credencial para outro endereço.
        return None


def load_configuration() -> tuple[str, str]:
    api_url = os.getenv("SCOUT_API_URL", "").strip().rstrip("/")
    token = os.getenv("SCOUT_AGENT_TOKEN", "").strip()

    if not api_url:
        raise ValueError("Configure a variável SCOUT_API_URL.")

    if not token:
        raise ValueError("Configure a variável SCOUT_AGENT_TOKEN.")

    parsed_url = urlsplit(api_url)

    if (
        not parsed_url.hostname
        or parsed_url.username is not None
        or parsed_url.password is not None
        or parsed_url.query
        or parsed_url.fragment
    ):
        raise ValueError("SCOUT_API_URL possui formato inválido.")

    local_hosts = {"localhost", "127.0.0.1", "::1"}

    if parsed_url.scheme != "https":
        local_http = (
            parsed_url.scheme == "http"
            and parsed_url.hostname in local_hosts
        )

        if not local_http:
            raise ValueError(
                "Use HTTPS para conectar a uma API remota. "
                "HTTP é permitido apenas nos testes locais."
            )

    return api_url, token


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

    except (URLError, TimeoutError, OSError):
        logger.warning(
            "Não foi possível comunicar com a API. "
            "Uma nova tentativa será feita no próximo ciclo."
        )
        return False

    logger.info("Heartbeat aceito pela API.")
    return True


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

    opener = build_opener(NoRedirectHandler())

    logger.info(
        "Scout Agent %s iniciado. Intervalo de heartbeat: %s segundos.",
        AGENT_VERSION,
        HEARTBEAT_INTERVAL_SECONDS,
    )

    try:
        while True:
            cycle_start = time.monotonic()

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