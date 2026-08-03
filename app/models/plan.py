from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.subscription import Subscription

#class Plan representa a tabela de planos no banco de dados.
class Plan(BaseModel):
    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=0)

    max_customers: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_servers: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    max_users: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    agent_auto_update: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    #Relacionamento com a tabela de assinaturas, permitindo acessar todas as assinaturas associadas a este plano.
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="plan",
        lazy="selectin",
    )