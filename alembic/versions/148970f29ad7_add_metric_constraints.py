"""add metric constraints

Revision ID: 148970f29ad7
Revises: a1e9958a8cb3
Create Date: 2026-09-07 19:01:11.072700

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '148970f29ad7'
down_revision: Union[str, Sequence[str], None] = 'a1e9958a8cb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_check_constraint(
        "ck_metrics_network_in_positive",
        "metrics",
        "network_in_bytes >= 0",
    )

    op.create_check_constraint(
        "ck_metrics_network_out_positive",
        "metrics",
        "network_out_bytes >= 0",
    )

    op.create_check_constraint(
        "ck_metrics_process_count_positive",
        "metrics",
        "process_count >= 0",
    )

    op.create_check_constraint(
        "ck_metrics_uptime_positive",
        "metrics",
        "uptime_seconds >= 0",
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_constraint(
        "ck_metrics_uptime_positive",
        "metrics",
        type_="check",
    )

    op.drop_constraint(
        "ck_metrics_process_count_positive",
        "metrics",
        type_="check",
    )

    op.drop_constraint(
        "ck_metrics_network_out_positive",
        "metrics",
        type_="check",
    )

    op.drop_constraint(
        "ck_metrics_network_in_positive",
        "metrics",
        type_="check",
    )