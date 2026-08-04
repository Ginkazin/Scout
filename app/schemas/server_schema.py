import uuid
from pydantic import Field, IPvAnyAddress
from app.models.server import ServerType
from app.schemas.base_schema import BaseSchema, BaseResponseSchema

#class ServerBase é uma classe base para os schemas de servidor, fornecendo campos comuns como name, server_type, hostname, ip_address, operating_system e description.
class ServerBase(BaseSchema):
    name: str = Field(min_length=2, max_length=120)
    server_type: ServerType = ServerType.VPS
    hostname: str | None = Field(default=None, max_length=255)
    ip_address: IPvAnyAddress | None = None
    operating_system: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


class ServerCreate(ServerBase):
    """Sem customer_id — vem do path da rota (/customers/{customer_id}/servers)."""
    pass

# ServerUpdate é uma classe para atualizar informações de um servidor, permitindo a modificação de campos como name, server_type, hostname, ip_address, operating_system, description e is_active.
class ServerUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    server_type: ServerType | None = None
    hostname: str | None = Field(default=None, max_length=255)
    ip_address: IPvAnyAddress | None = None
    operating_system: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None

# ServerResponse é uma classe para representar a resposta de um servidor, incluindo campos como customer_id, name, server_type, hostname, ip_address, operating_system, description e is_active.
class ServerResponse(BaseResponseSchema):
    customer_id: uuid.UUID
    name: str
    server_type: ServerType
    hostname: str | None
    ip_address: IPvAnyAddress | None
    operating_system: str | None
    description: str | None
    is_active: bool