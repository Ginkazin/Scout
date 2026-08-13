import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from scripts.cleanup_old_metrics import cleanup_old_metrics

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")

# Executa a função de limpeza de métricas antigas, capturando e registrando qualquer exceção que ocorra durante a execução.
async def _run_cleanup_job() -> None:
    try:
        await cleanup_old_metrics()
    except Exception:
        logger.exception("Erro ao executar limpeza de métricas antigas")

# Inicia o agendador de tarefas, adicionando um job para executar a limpeza de métricas antigas todos os dias às 03:00. Se o job já existir, ele será substituído. O agendador é iniciado e uma mensagem de log é registrada.
def start_scheduler() -> None:
    scheduler.add_job(
        _run_cleanup_job,
        trigger=CronTrigger(hour=3, minute=0),
        id="cleanup_old_metrics",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    logger.info("Scheduler iniciado — limpeza de métricas agendada para 03:00.")

# Encerra o agendador de tarefas, desligando-o e liberando os recursos associados.
def stop_scheduler() -> None:
    scheduler.shutdown()