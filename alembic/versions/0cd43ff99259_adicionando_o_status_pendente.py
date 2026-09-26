"""adicionando o status pendente

Revision ID: 0cd43ff99259
Revises: 148970f29ad7
Create Date: 2026-09-26 19:53:44.476929

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0cd43ff99259'
down_revision: Union[str, Sequence[str], None] = '148970f29ad7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE agent_status ADD VALUE IF NOT EXISTS 'PENDING'"
    )


def downgrade() -> None:
    raise NotImplementedError(
        "A remoção de PENDING exige recriar o enum agent_status "
        "e definir como converter os registros existentes."
    )
