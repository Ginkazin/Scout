from datetime import datetime
from uuid import UUID

from app.models.subscription import PaymentProvider, SubscriptionStatus
from app.schemas.base_schema import BaseSchema, BaseResponseSchema


class SubscriptionCreate(BaseSchema):
    plan_id: UUID
    payment_provider: PaymentProvider | None = None
    provider_customer_id: str | None = None
    provider_subscription_id: str | None = None
    trial_ends_at: datetime | None = None


class SubscriptionUpdate(BaseSchema):
    plan_id: UUID | None = None
    status: SubscriptionStatus | None = None
    payment_provider: PaymentProvider | None = None
    provider_customer_id: str | None = None
    provider_subscription_id: str | None = None
    trial_ends_at: datetime | None = None
    renews_at: datetime | None = None
    canceled_at: datetime | None = None


class SubscriptionResponse(BaseResponseSchema):
    user_id: UUID
    plan_id: UUID
    status: SubscriptionStatus
    payment_provider: PaymentProvider | None
    provider_customer_id: str | None
    provider_subscription_id: str | None
    starts_at: datetime
    trial_ends_at: datetime | None
    renews_at: datetime | None
    canceled_at: datetime | None