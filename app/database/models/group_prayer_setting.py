from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.database.models.prayer_schedule import PRAYER_NAMES

if TYPE_CHECKING:
    from app.database.models.group import Group

DEFAULT_PRAYER_TOGGLES: dict[str, bool] = {
    "fajr": False,
    "zuhr": True,
    "asr": True,
    "maghrib": True,
    "isha": False,
}


class GroupPrayerSetting(Base):
    __tablename__ = "group_prayer_settings"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    prayer_name: Mapped[str] = mapped_column(sa.String(10), nullable=False)
    enabled: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)

    __table_args__ = (
        sa.UniqueConstraint("group_id", "prayer_name", name="uq_group_prayer_settings_group_prayer"),
        sa.CheckConstraint(
            "prayer_name IN ('fajr','zuhr','asr','maghrib','isha')",
            name="ck_group_prayer_settings_valid_name",
        ),
    )

    group: Mapped["Group"] = relationship(back_populates="prayer_settings")


assert set(DEFAULT_PRAYER_TOGGLES) == set(PRAYER_NAMES)
