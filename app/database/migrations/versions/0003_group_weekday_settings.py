"""group weekday settings

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-10

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "group_weekday_settings",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.BigInteger(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("group_id", "weekday", name="uq_group_weekday_settings_group_weekday"),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_group_weekday_settings_valid_weekday"),
    )
    # Backfill defaults for existing groups: Mon-Fri on, Sat/Sun off.
    op.execute(
        """
        INSERT INTO group_weekday_settings (group_id, weekday, enabled)
        SELECT g.id, d.weekday, d.weekday < 5
        FROM groups g CROSS JOIN generate_series(0, 6) AS d(weekday)
        """
    )


def downgrade() -> None:
    op.drop_table("group_weekday_settings")
