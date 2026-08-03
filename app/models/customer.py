import uuid
from pydantic import Field
from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING
from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.server import Server

#class Customer representa a tabela de clientes no banco de dados.
class Customer(BaseModel):
    __tablename__ = "customers"

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_customer_user_name"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True)

    # Nome do cliente (Ex.: João da Silva)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    # Empresa do cliente (Ex.: Mercado XPTO)
    company: Mapped[str | None] = mapped_column(String(120), nullable=True)

    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Observações gerais
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relacionamentos
    #usuario proprietário do cliente.
    user: Mapped["User"] = relationship(back_populates="customers", lazy="selectin")

    #servidores pertencentes ao cliente.
    servers: Mapped[list["Server"]] = relationship(
    back_populates="customer", cascade="all, delete-orphan", passive_deletes=True, lazy="selectin")