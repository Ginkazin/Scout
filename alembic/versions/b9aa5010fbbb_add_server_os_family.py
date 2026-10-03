"""add server os family

Revision ID: b9aa5010fbbb
Revises: 3d39fef6b8b9
Create Date: 2026-10-03 10:10:38.386416

"""
from typing import Sequence, Union
from sqlalchemy.dialects import postgresql
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9aa5010fbbb'
down_revision: Union[str, Sequence[str], None] = '3d39fef6b8b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    os_family = postgresql.ENUM(
        "WINDOWS",
        "LINUX",
        name="server_os_family",
        create_type=False,
    )

    os_family.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "servers",
        sa.Column(
            "os_family",
            os_family,
            nullable=True,
        ),
    )

    # Classifica apenas valores antigos inequívocos.
    # Outros textos e valores ausentes continuam sem classificação.
    op.execute(
        """
        UPDATE servers
        SET os_family = CASE
            WHEN lower(trim(operating_system)) = 'windows'
                THEN 'WINDOWS'::server_os_family
            WHEN lower(trim(operating_system)) = 'linux'
                THEN 'LINUX'::server_os_family
        END
        WHERE lower(trim(operating_system)) IN ('windows', 'linux')
        """
    )


def downgrade() -> None:
    op.drop_column("servers", "os_family")

    os_family = postgresql.ENUM(
        "WINDOWS",
        "LINUX",
        name="server_os_family",
        create_type=False,
    )

    os_family.drop(op.get_bind(), checkfirst=True)