import enum
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import BaseModel
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.plan import Plan

#class SubscriptionStatus define os diferentes status que uma assinatura pode ter no sistema.
class SubscriptionStatus(str, enum.Enum):
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    PAST_DUE = "PAST_DUE"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"

#class PaymentProvider define os diferentes provedores de pagamento que podem ser usados para gerenciar assinaturas.
class PaymentProvider(str, enum.Enum):
    STRIPE = "STRIPE"
    MERCADO_PAGO = "MERCADO_PAGO"
    MANUAL = "MANUAL"


#class Subscription representa a tabela de assinaturas no banco de dados.
class Subscription(BaseModel):
    __tablename__ = "subscriptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, unique=True
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("plans.id"), nullable=False, index=True
    )

    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"),
        default=SubscriptionStatus.TRIAL,
        nullable=False,
    )

    payment_provider: Mapped[PaymentProvider | None] = mapped_column(
        Enum(PaymentProvider, name="payment_provider"),
        nullable=True,
    )
    provider_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    starts_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    renews_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    #Relacionamento com a tabela de usuários, permitindo acessar o usuário associado a esta assinatura.
    user: Mapped["User"] = relationship(
        back_populates="subscription",
        lazy="selectin",
    )
    #Relacionamento com a tabela de planos, permitindo acessar o plano associado a esta assinatura.
    plan: Mapped["Plan"] = relationship(
        back_populates="subscriptions",
        lazy="selectin",
    )