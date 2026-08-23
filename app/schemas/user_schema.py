from pydantic import EmailStr, Field, field_validator

from app.models.user import UserRole
from app.schemas.base_schema import BaseSchema, BaseResponseSchema
from datetime import datetime
from app.core.security import validate_password_strength

# Schemas relacionados ao usuário, incluindo criação, atualização e resposta de dados do usuário. Estes schemas são usados para validação de entrada e saída de dados na API.
class UserBase(BaseSchema):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr

#Uso exclusivo em rota pública de registro (/auth/register).
class UserCreate(UserBase):

    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)

#Uso exclusivo em rota administrativa (/admin/users).
class UserCreateAdmin(UserBase):

    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.MEMBER
    is_active: bool = True

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return validate_password_strength(v)

#Atualização de dados de perfil. NÃO inclui senha e nem email — 
class UserUpdate(BaseSchema):

    name: str | None = Field(default=None, min_length=2, max_length=120)

#Uso exclusivo em rota dedicada (/users/me/change-password), exige senha atual.
class UserChangePassword(BaseSchema):

    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        return validate_password_strength(v)

#Resposta de dados do usuário.
class UserResponse(BaseResponseSchema):
    name: str
    email: EmailStr
    role: UserRole
    email_verified: bool
    is_active: bool
    last_login: datetime | None      