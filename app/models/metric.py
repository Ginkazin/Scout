import uuid
from sqlalchemy import BigInteger, CheckConstraint, Float, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.server import Server

#class Metric representa a tabela de métricas coletadas dos servidores monitorados. 
class Metric(BaseModel):
    __tablename__ = "metrics"
    __table_args__ = (
        Index("ix_metrics_server_created_at", "server_id", "created_at"),
        CheckConstraint("cpu_usage >= 0 AND cpu_usage <= 100", name="ck_metrics_cpu_range"),
        CheckConstraint("memory_usage >= 0 AND memory_usage <= 100", name="ck_metrics_memory_range"),
        CheckConstraint("disk_usage >= 0 AND disk_usage <= 100", name="ck_metrics_disk_range"),
        CheckConstraint(
            "response_time_ms IS NULL OR response_time_ms >= 0",
            name="ck_metrics_response_time_positive",
        ),
    )

    server_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"),
        nullable=False,
    )

    cpu_usage: Mapped[float] = mapped_column(Float, nullable=False)
    memory_usage: Mapped[float] = mapped_column(Float, nullable=False)
    disk_usage: Mapped[float] = mapped_column(Float, nullable=False)
    network_in_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    network_out_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    process_count: Mapped[int] = mapped_column(Integer, nullable=False)
    uptime_seconds: Mapped[int] = mapped_column(BigInteger, nullable=False)
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    server: Mapped["Server"] = relationship(
        back_populates="metrics",
        lazy="raise",
    )