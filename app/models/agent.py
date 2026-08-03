import enum
import uuid
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.server import Server

#class AgentStatus define os diferentes status que um agente pode ter no sistema.
class AgentStatus(str, enum.Enum):
    OFFLINE = "OFFLINE"
    ONLINE = "ONLINE"
    DISABLED = "DISABLED"

#class Agent representa a tabela de agentes no banco de dados.
class Agent(BaseModel):
    __tablename__ = "agents"

    server_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("servers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Hash do token usado pelo agente para autenticação.
    # O valor em texto puro é gerado na criação, devolvido UMA ÚNICA VEZ
    # na resposta da API, e nunca fica armazenado — apenas o hash.
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False,)

    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")

    status: Mapped[AgentStatus] = mapped_column(
        Enum(AgentStatus, name="agent_status"),
        nullable=False,
        default=AgentStatus.OFFLINE,
    )

    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auto_update: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relacionamentos
    server: Mapped["Server"] = relationship(
        back_populates="agent",
        lazy="selectin",
    )