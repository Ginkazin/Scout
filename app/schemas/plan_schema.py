from decimal import Decimal

from pydantic import Field

from app.schemas.base_schema import BaseSchema, BaseResponseSchema

# schema de planos de assinatura do sistema
class PlanBase(BaseSchema):
    name: str = Field(min_length=2, max_length=35)
    price: Decimal = Field(ge=0, decimal_places=2)
    max_customers: int = Field(ge=1)
    max_servers: int = Field(ge=1)
    max_users: int = Field(ge=1)
    retention_days: int = Field(ge=1)
    agent_auto_update: bool = True

class PlanCreate(PlanBase):
    pass

# schema para atualização de planos de assinatura do sistema
class PlanUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=2, max_length=50)
    price: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    max_customers: int | None = Field(default=None, ge=1)
    max_servers: int | None = Field(default=None, ge=1)
    max_users: int | None = Field(default=None, ge=1)
    retention_days: int | None = Field(default=None, ge=1)
    agent_auto_update: bool | None = None
    is_active: bool | None = None

# schema de resposta de planos de assinatura do sistema
class PlanResponse(BaseResponseSchema):
    name: str
    price: Decimal
    max_customers: int
    max_servers: int
    max_users: int
    retention_days: int
    agent_auto_update: bool
    is_active: bool