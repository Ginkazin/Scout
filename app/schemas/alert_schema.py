import uuid
from datetime import datetime
from app.models.alert import AlertSeverity, AlertStatus
from app.schemas.base_schema import BaseSchema, BaseResponseSchema

#class AlertCreate é uma classe para criar alertas, herdando os campos da classe BaseSchema e adicionando campos específicos como server_id, severity, status, metric_name, metric_value, threshold, title, description e resolved_at.
class AlertResponse(BaseResponseSchema):
    server_id: uuid.UUID

    severity: AlertSeverity
    status: AlertStatus

    metric_name: str
    metric_value: float
    threshold: float

    title: str
    description: str | None

    resolved_at: datetime | None