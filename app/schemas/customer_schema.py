from pydantic import EmailStr, Field
from app.schemas.base_schema import BaseSchema, BaseResponseSchema

#class CustomerBase é uma classe base para os schemas de cliente, fornecendo campos comuns como name, company, email, phone e notes.
class CustomerBase(BaseSchema):
    name: str = Field(min_length=3, max_length=120)
    company: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    notes: str | None = Field(default=None, max_length=2000)

#class CustomerCreate é uma classe para criar um novo cliente, herdando os campos da classe CustomerBase.
class CustomerCreate(CustomerBase):
    pass

#class CustomerUpdate é uma classe para atualizar informações de um cliente, permitindo a modificação de campos como name, company, email, phone, notes e is_active.
class CustomerUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=3, max_length=120)
    company: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    notes: str | None = Field(default=None, max_length=2000)
    is_active: bool | None = None

#class CustomerResponse é uma classe para representar a resposta de um cliente, incluindo campos como name, company, email, phone, notes e is_active.
class CustomerResponse(BaseResponseSchema):
    name: str
    company: str | None
    email: str | None
    phone: str | None
    notes: str | None
    is_active: bool