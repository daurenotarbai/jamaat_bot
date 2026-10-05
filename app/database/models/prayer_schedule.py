from datetime import date, datetime, time
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.group import Group

PRAYER_NAMES = ("fajr", "zuhr", "asr", "maghrib", "isha")


class PrayerSchedule(Base):
    __tablename__ = "prayer_schedules"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    date: Mapped[date] = mapped_column(sa.Date, nullable=False)
    prayer_name: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    prayer_time: Mapped[time] = mapped_column(sa.Time, nullable=False)
    notification_sent: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.false())
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())

    __table_args__ = (
        sa.UniqueConstraint("group_id", "date", "prayer_name", name="uq_prayer_schedules_group_date_prayer"),
        sa.CheckConstraint(
            "prayer_name IN ('fajr','zuhr','asr','maghrib','isha')",
            name="ck_prayer_schedules_valid_name",
        ),
        sa.Index("ix_prayer_schedules_pending", "notification_sent", "date"),
        sa.Index("ix_prayer_schedules_group_date", "group_id", "date"),
    )

    group: Mapped["Group"] = relationship(back_populates="schedules")
