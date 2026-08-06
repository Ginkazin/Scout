import enum
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.subscription import Subscription
    from app.models.customer import Customer

#class UserRole define os diferentes papéis que um usuário pode ter no sistema.
class UserRole(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"

#class User representa a tabela de usuários no banco de dados.
class User(BaseModel):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.ADMIN,
        nullable=False,
    )
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    #Relacionamento com a tabela de assinaturas, permitindo acessar a assinatura associada a este usuário.
    subscription: Mapped["Subscription"] = relationship(
        back_populates="user",
        uselist=False,
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    #Relacionamento com a tabela de clientes.
    customers: Mapped[list["Customer"]] = relationship(
    back_populates="user",
    lazy="selectin",
    )
    