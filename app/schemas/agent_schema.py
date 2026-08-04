import uuid
from datetime import datetime
from pydantic import Field
from app.models.agent import AgentStatus
from app.schemas.base_schema import BaseSchema, BaseResponseSchema

#class AgentCreate é uma classe para criar um novo agente, herdando os campos da classe BaseSchema.
class AgentCreate(BaseSchema):
    pass

#class AgentUpdate é uma classe para atualizar informações de um agente, permitindo a modificação do campo auto_update.
class AgentUpdate(BaseSchema):
    auto_update: bool | None = None

#class AgentResponse é uma classe para representar a resposta de um agente, herdando os campos da classe BaseResponseSchema.
class AgentResponse(BaseResponseSchema):
    server_id: uuid.UUID
    version: str
    status: AgentStatus
    last_seen_at: datetime | None
    auto_update: bool

#class AgentHeartbeat é uma classe para representar o heartbeat de um agente, incluindo o campo version.
class AgentHeartbeat(BaseSchema):
    version: str = Field(min_length=1, max_length=20)

#class AgentCreateResponse é uma classe para representar a resposta de criação de um agente, herdando os campos da classe AgentResponse e adicionando o campo token.
class AgentCreateResponse(AgentResponse):
    token: str