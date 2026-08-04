import uuid
from datetime import datetime

from app.models.alert import AlertSeverity, AlertStatus, MetricType
from app.schemas.base_schema import BaseSchema, BaseResponseSchema


class AlertResponse(BaseResponseSchema):
    server_id: uuid.UUID

    severity: AlertSeverity
    status: AlertStatus

    metric_name: MetricType
    metric_value: float
    threshold: float

    title: str
    description: str | None

    resolved_at: datetime | None