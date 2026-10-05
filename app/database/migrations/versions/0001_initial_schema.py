"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "groups",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("city", sa.String(255), nullable=True),
        sa.Column("city_slug", sa.String(255), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=True),
        sa.Column("utc_offset_minutes", sa.Integer(), nullable=True),
        sa.Column("prepare_pray_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("juma_notification_time", sa.Time(), nullable=False, server_default="12:30:00"),
        sa.Column("calculation_method", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("telegram_chat_id", name="uq_groups_telegram_chat_id"),
        sa.CheckConstraint("prepare_pray_minutes > 0", name="ck_groups_prepare_minutes_positive"),
    )
    op.create_index("ix_groups_telegram_chat_id", "groups", ["telegram_chat_id"])
    op.create_index("ix_groups_is_active", "groups", ["is_active"])

    op.create_table(
        "prayer_schedules",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.BigInteger(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("prayer_name", sa.String(10), nullable=False),
        sa.Column("prayer_time", sa.Time(), nullable=False),
        sa.Column("notification_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("group_id", "date", "prayer_name", name="uq_prayer_schedules_group_date_prayer"),
        sa.CheckConstraint(
            "prayer_name IN ('fajr','zuhr','asr','maghrib','isha')",
            name="ck_prayer_schedules_valid_name",
        ),
    )
    op.create_index("ix_prayer_schedules_pending", "prayer_schedules", ["notification_sent", "date"])
    op.create_index("ix_prayer_schedules_group_date", "prayer_schedules", ["group_id", "date"])

    op.create_table(
        "group_prayer_settings",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.BigInteger(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prayer_name", sa.String(10), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("group_id", "prayer_name", name="uq_group_prayer_settings_group_prayer"),
        sa.CheckConstraint(
            "prayer_name IN ('fajr','zuhr','asr','maghrib','isha')",
            name="ck_group_prayer_settings_valid_name",
        ),
    )

    op.create_table(
        "polls",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.BigInteger(), sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("prayer_name", sa.String(10), nullable=False),
        sa.Column("telegram_message_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_poll_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("group_id", "date", "type", "prayer_name", name="uq_polls_group_date_type_prayer"),
        sa.UniqueConstraint("telegram_poll_id", name="uq_polls_telegram_poll_id"),
        sa.CheckConstraint("type IN ('prayer','juma')", name="ck_polls_valid_type"),
        sa.CheckConstraint(
            "(type = 'juma' AND prayer_name = 'juma') OR (type = 'prayer' AND prayer_name != 'juma')",
            name="ck_polls_type_prayer_consistency",
        ),
    )


def downgrade() -> None:
    op.drop_table("polls")
    op.drop_table("group_prayer_settings")
    op.drop_index("ix_prayer_schedules_group_date", table_name="prayer_schedules")
    op.drop_index("ix_prayer_schedules_pending", table_name="prayer_schedules")
    op.drop_table("prayer_schedules")
    op.drop_index("ix_groups_is_active", table_name="groups")
    op.drop_index("ix_groups_telegram_chat_id", table_name="groups")
    op.drop_table("groups")
