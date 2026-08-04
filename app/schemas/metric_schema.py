import uuid
from pydantic import Field
from app.schemas.base_schema import BaseSchema, BaseResponseSchema

#class MetricCreate é uma classe para criar métricas, herdando os campos da classe BaseSchema e adicionando campos específicos como cpu_usage, memory_usage, disk_usage, network_in_bytes, network_out_bytes, process_count, uptime_seconds e response_time_ms.
class MetricCreate(BaseSchema):
    cpu_usage: float = Field(ge=0, le=100)
    memory_usage: float = Field(ge=0, le=100)
    disk_usage: float = Field(ge=0, le=100)

    network_in_bytes: int = Field(ge=0)
    network_out_bytes: int = Field(ge=0)

    process_count: int = Field(ge=0)
    uptime_seconds: int = Field(ge=0)

    response_time_ms: int | None = Field(
        default=None,
        ge=0,
    )

#class MetricResponse é uma classe para representar a resposta de métricas, herdando os campos da classe BaseResponseSchema e adicionando campos específicos como server_id, cpu_usage, memory_usage, disk_usage, network_in_bytes, network_out_bytes, process_count, uptime_seconds e response_time_ms.
class MetricResponse(BaseResponseSchema):
    server_id: uuid.UUID

    cpu_usage: float
    memory_usage: float
    disk_usage: float

    network_in_bytes: int
    network_out_bytes: int

    process_count: int
    uptime_seconds: int

    response_time_ms: int | None