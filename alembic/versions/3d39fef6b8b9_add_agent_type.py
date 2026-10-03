"""add agent type

Revision ID: 3d39fef6b8b9
Revises: 0cd43ff99259
Create Date: 2026-10-03 09:45:56.864570

"""
from typing import Sequence, Union
from sqlalchemy.dialects import postgresql 
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3d39fef6b8b9'
down_revision: Union[str, Sequence[str], None] = '0cd43ff99259'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    agent_type = postgresql.ENUM(
        "INFRASTRUCTURE",
        "DATABASE",
        name="agent_type",
        create_type=False,
    )

    agent_type.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "agents",
        sa.Column(
            "agent_type",
            agent_type,
            nullable=False,
            server_default="INFRASTRUCTURE",
        ),
    )


def downgrade() -> None:
    op.drop_column("agents", "agent_type")

    agent_type = postgresql.ENUM(
        "INFRASTRUCTURE",
        "DATABASE",
        name="agent_type",
        create_type=False,
    )

    agent_type.drop(op.get_bind(), checkfirst=True)