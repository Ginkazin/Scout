from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime

# BaseSchema e BaseResponseSchema são classes base para os schemas do Pydantic, fornecendo configurações comuns e campos padrão para os modelos de dados.
class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        extra="forbid",
        str_strip_whitespace=True,
    )

# BaseResponseSchema é uma classe base para respostas de API, incluindo campos comuns como id, created_at e updated_at.
class BaseResponseSchema(BaseSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime