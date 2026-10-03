import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from scripts.cleanup_old_metrics import cleanup_old_metrics
from app.core.config import settings
from scripts.check_offline_agents import check_offline_agents

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")

# Executa a função de limpeza de métricas antigas, capturando e registrando qualquer exceção que ocorra durante a execução.
async def _run_cleanup_job() -> None:
    try:
        await cleanup_old_metrics()
    except Exception:
        logger.exception("Erro ao executar limpeza de métricas antigas")

# Executa a função de verificação de agentes offline, capturando e registrando qualquer exceção que ocorra durante a execução.
async def _run_offline_check_job() -> None:
    try:
        await check_offline_agents()
    except Exception:
        logger.exception(
            "Erro ao verificar agentes sem heartbeat"
        )

# Inicia o agendador de tarefas, adicionando um job para executar a limpeza de métricas antigas todos os dias às 03:00. Se o job já existir, ele será substituído. O agendador é iniciado e uma mensagem de log é registrada.
def start_scheduler() -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        _run_cleanup_job,
        trigger=CronTrigger(
            hour=3,
            minute=0,
            timezone="America/Sao_Paulo"
        ),
        id="cleanup_old_metrics",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    scheduler.add_job(
        _run_offline_check_job,
        trigger="interval",
        seconds=settings.AGENT_OFFLINE_CHECK_INTERVAL_SECONDS,
        id="check_offline_agents",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()

    logger.info(
        "Scheduler iniciado — limpeza de métricas agendada para 03:00."
    )

# Encerra o agendador de tarefas, desligando-o e liberando os recursos associados.
def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()

        logger.info("Scheduler encerrado.")