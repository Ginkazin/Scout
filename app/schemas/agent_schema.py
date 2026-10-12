import uuid
from datetime import datetime
from pydantic import Field, SecretStr
from app.models.server import ServerOSFamily
from app.models.agent import AgentStatus, AgentType
from app.schemas.base_schema import BaseSchema, BaseResponseSchema

#class AgentCreate é uma classe para criar um novo agente, herdando os campos da classe BaseSchema.
class AgentCreate(BaseSchema):
    agent_type: AgentType

#class AgentUpdate é uma classe para atualizar informações de um agente, permitindo a modificação do campo auto_update.
class AgentUpdate(BaseSchema):
    auto_update: bool | None = None

#class AgentResponse é uma classe para representar a resposta de um agente, herdando os campos da classe BaseResponseSchema.
class AgentResponse(BaseResponseSchema):
    server_id: uuid.UUID
    agent_type: AgentType
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

# class AgentUpdateResponse é uma classe para representar a resposta de atualização de um agente, herdando os campos da classe AgentResponse.
class AgentRuntimeConfig(BaseSchema):
    agent_id: uuid.UUID
    server_id: uuid.UUID
    agent_type: AgentType
    server_os_family: ServerOSFamily

# class usada para representar a resposta de criação de um código de instalação de agente, incluindo o ID do agente, o código de instalação e a data de expiração.
class AgentInstallationCodeResponse(BaseSchema):
    agent_id: uuid.UUID
    installation_code: str
    expires_at: datetime

# class usada para representar a solicitação de ativação de um agente, incluindo o código de instalação e a família do sistema operacional do servidor.
class AgentActivationRequest(BaseSchema):
    installation_code: SecretStr
    os_family: ServerOSFamily

# class usada para representar a resposta de ativação de um agente, herdando os campos da classe AgentRuntimeConfig e adicionando o campo token.
class AgentActivationResponse(AgentRuntimeConfig):
    token: str
