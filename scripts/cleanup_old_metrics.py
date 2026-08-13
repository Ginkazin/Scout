import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, select
from app.core.database import SessionLocal
from app.models.customer import Customer
from app.models.metric import Metric
from app.models.plan import Plan
from app.models.server import Server
from app.models.subscription import Subscription

logger = logging.getLogger(__name__)

#Remove métricas mais antigas que o retention_days do plano de cada assinante. Pensado para rodar em horário de baixo uso (madrugada)
async def cleanup_old_metrics() -> None:
 

    logger.info("Iniciando limpeza de métricas antigas...")
    total_deleted = 0

    async with SessionLocal() as db:
        result = await db.execute(
            select(Subscription.user_id, Plan.retention_days).join(
                Plan, Subscription.plan_id == Plan.id
            )
        )

        for user_id, retention_days in result.all():
            cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

            server_ids_subquery = (
                select(Server.id)
                .join(Customer, Server.customer_id == Customer.id)
                .where(Customer.user_id == user_id)
            )

            delete_result = await db.execute(
                delete(Metric)
                .where(Metric.server_id.in_(server_ids_subquery))
                .where(Metric.created_at < cutoff)
            )
            total_deleted += delete_result.rowcount

        await db.commit()

    logger.info(f"Limpeza concluída. {total_deleted} métricas removidas.")


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)
    asyncio.run(cleanup_old_metrics())