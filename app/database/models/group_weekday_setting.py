from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.database.models.group import Group

# Python weekday numbering: Monday=0 ... Sunday=6.
WEEKDAYS: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)

DEFAULT_WEEKDAY_TOGGLES: dict[int, bool] = {
    0: True,
    1: True,
    2: True,
    3: True,
    4: True,
    5: False,
    6: False,
}


class GroupWeekdaySetting(Base):
    __tablename__ = "group_weekday_settings"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(sa.ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    weekday: Mapped[int] = mapped_column(sa.SmallInteger, nullable=False)
    enabled: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)

    __table_args__ = (
        sa.UniqueConstraint("group_id", "weekday", name="uq_group_weekday_settings_group_weekday"),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_group_weekday_settings_valid_weekday"),
    )

    group: Mapped["Group"] = relationship(back_populates="weekday_settings")


assert set(DEFAULT_WEEKDAY_TOGGLES) == set(WEEKDAYS)
