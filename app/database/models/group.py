from datetime import datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.group_prayer_setting import GroupPrayerSetting
    from app.database.models.group_weekday_setting import GroupWeekdaySetting
    from app.database.models.poll import Poll
    from app.database.models.prayer_schedule import PrayerSchedule


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    telegram_chat_id: Mapped[int] = mapped_column(sa.BigInteger, nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(sa.String(255), nullable=False)

    city: Mapped[str | None] = mapped_column(sa.String(255))
    city_slug: Mapped[str | None] = mapped_column(sa.String(255))
    latitude: Mapped[Decimal | None] = mapped_column(sa.Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(sa.Numeric(9, 6))
    timezone: Mapped[str | None] = mapped_column(sa.String(50))
    utc_offset_minutes: Mapped[int | None] = mapped_column(sa.Integer)

    prepare_pray_minutes: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default="15")
    juma_notification_time: Mapped[time] = mapped_column(sa.Time, nullable=False, server_default="12:30:00")
    calculation_method: Mapped[str | None] = mapped_column(sa.String(50))

    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.true())

    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()
    )

    __table_args__ = (
        sa.CheckConstraint("prepare_pray_minutes > 0", name="ck_groups_prepare_minutes_positive"),
        sa.Index("ix_groups_is_active", "is_active"),
    )

    schedules: Mapped[list["PrayerSchedule"]] = relationship(
        back_populates="group", cascade="all, delete-orphan", passive_deletes=True
    )
    prayer_settings: Mapped[list["GroupPrayerSetting"]] = relationship(
        back_populates="group", cascade="all, delete-orphan", passive_deletes=True
    )
    weekday_settings: Mapped[list["GroupWeekdaySetting"]] = relationship(
        back_populates="group", cascade="all, delete-orphan", passive_deletes=True
    )
    polls: Mapped[list["Poll"]] = relationship(
        back_populates="group", cascade="all, delete-orphan", passive_deletes=True
    )

    @property
    def has_location(self) -> bool:
        return self.latitude is not None and self.longitude is not None and self.utc_offset_minutes is not None
