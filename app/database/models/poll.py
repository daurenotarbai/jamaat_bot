from datetime import date, datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.group import Group

JUMA_SENTINEL = "juma"


class Poll(Base):
    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    type: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    prayer_name: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    telegram_message_id: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    telegram_poll_id: Mapped[str] = mapped_column(sa.String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())

    __table_args__ = (
        sa.UniqueConstraint("group_id", "date", "type", "prayer_name", name="uq_polls_group_date_type_prayer"),
        sa.CheckConstraint("type IN ('prayer','juma')", name="ck_polls_valid_type"),
        sa.CheckConstraint(
            "(type = 'juma' AND prayer_name = 'juma') OR (type = 'prayer' AND prayer_name != 'juma')",
            name="ck_polls_type_prayer_consistency",
        ),
    )

    group: Mapped["Group"] = relationship(back_populates="polls")
