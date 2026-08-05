import uuid
from datetime import datetime
from app.models.alert import AlertSeverity, AlertStatus
from app.schemas.base_schema import BaseSchema, BaseResponseSchema

#Uso interno — criado pelo serviço de avaliação de métricas quando uma regra é violada. Não é uma rota pública de criação.
class AlertCreate(BaseSchema):
    server_id: uuid.UUID
    severity: AlertSeverity
    metric_name: str
    metric_value: float
    threshold: float
    title: str
    description: str | None = None

#Uso do usuário via painel — reconhecer ou resolver um alerta. Conteúdo do alerta (severity, valores, título) não é editável
class AlertUpdate(BaseSchema):
    status: AlertStatus

#Resposta do serviço de alerta para o usuário via painel — não é editável, apenas leitura
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