import enum
import uuid
from sqlalchemy import Boolean, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.agent import Agent
    from app.models.metric import Metric
    from app.models.alert import Alert

#class ServerType define os diferentes tipos de servidores que podem ser registrados no sistema.
class ServerType(str, enum.Enum):
    VPS = "VPS"
    DEDICATED = "DEDICATED"
    CLOUD = "CLOUD"
    DATABASE = "DATABASE"
    DOCKER = "DOCKER"
    VM = "VM"
    OTHER = "OTHER"

#class Server representa a tabela de servidores no banco de dados.
class Server(BaseModel):
    __tablename__ = "servers"

    __table_args__ = (
        UniqueConstraint("customer_id", "name", name="uq_server_customer_name"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)

    server_type: Mapped[ServerType] = mapped_column(
        Enum(ServerType, name="server_type"),
        nullable=False,
        default=ServerType.VPS,
    )

    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)  # IPv4 e IPv6
    operating_system: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relacionamentos
    customer: Mapped["Customer"] = relationship(
        back_populates="servers",
        lazy="selectin",
    )
    agent: Mapped["Agent"] = relationship(
        back_populates="server",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )
    metrics: Mapped[list["Metric"]] = relationship(
        back_populates="server",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )
    alerts: Mapped[list["Alert"]] = relationship(
        back_populates="server",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )