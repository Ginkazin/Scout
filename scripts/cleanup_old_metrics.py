# scripts/cleanup_old_metrics.py

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, text

from app.core.database import SessionLocal
from app.models.customer import Customer
from app.models.metric import Metric
from app.models.plan import Plan
from app.models.server import Server
from app.models.subscription import Subscription


logger = logging.getLogger(__name__)

METRIC_RETENTION_LOCK_ID = 104729


async def cleanup_old_metrics() -> None:
    logger.info("Tentando iniciar limpeza de métricas antigas...")

    async with SessionLocal() as db:
        lock_acquired = await db.scalar(
            text(
                "SELECT pg_try_advisory_lock(:lock_id)"
            ),
            {
                "lock_id": METRIC_RETENTION_LOCK_ID,
            },
        )

        if not lock_acquired:
            logger.info(
                "Limpeza ignorada: outro worker já está executando o job."
            )
            return

        try:
            logger.info("Iniciando limpeza de métricas antigas...")

            total_deleted = 0

            result = await db.execute(
                select(
                    Subscription.user_id,
                    Plan.retention_days,
                ).join(
                    Plan,
                    Subscription.plan_id == Plan.id,
                )
            )

            for user_id, retention_days in result.all():
                cutoff = (
                    datetime.now(timezone.utc)
                    - timedelta(days=retention_days)
                )

                server_ids_subquery = (
                    select(Server.id)
                    .join(
                        Customer,
                        Server.customer_id == Customer.id,
                    )
                    .where(
                        Customer.user_id == user_id
                    )
                )

                delete_result = await db.execute(
                    delete(Metric)
                    .where(
                        Metric.server_id.in_(
                            server_ids_subquery
                        )
                    )
                    .where(
                        Metric.created_at < cutoff
                    )
                )

                total_deleted += delete_result.rowcount or 0

            await db.commit()

            logger.info(
                "Limpeza concluída. %s métricas removidas.",
                total_deleted,
            )

        except Exception:
            await db.rollback()
            logger.exception(
                "Erro durante limpeza de métricas antigas"
            )
            raise

        finally:
            await db.execute(
                text(
                    "SELECT pg_advisory_unlock(:lock_id)"
                ),
                {
                    "lock_id": METRIC_RETENTION_LOCK_ID,
                },
            )

            logger.debug(
                "Advisory lock da limpeza de métricas liberado."
            )