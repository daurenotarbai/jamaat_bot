import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.group_prayer_setting import DEFAULT_PRAYER_TOGGLES, GroupPrayerSetting
from app.database.models.prayer_schedule import PRAYER_NAMES


class GroupPrayerSettingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_defaults(self, group_id: int) -> None:
        stmt = pg_insert(GroupPrayerSetting).values(
            [
                {"group_id": group_id, "prayer_name": name, "enabled": enabled}
                for name, enabled in DEFAULT_PRAYER_TOGGLES.items()
            ]
        )
        stmt = stmt.on_conflict_do_nothing(index_elements=["group_id", "prayer_name"])
        await self._session.execute(stmt)

    async def get_all(self, group_id: int) -> dict[str, bool]:
        stmt = sa.select(GroupPrayerSetting.prayer_name, GroupPrayerSetting.enabled).where(
            GroupPrayerSetting.group_id == group_id
        )
        rows = await self._session.execute(stmt)
        settings = dict(rows.all())
        # Defensive default for any prayer missing a row (should not normally happen).
        for name in PRAYER_NAMES:
            settings.setdefault(name, DEFAULT_PRAYER_TOGGLES[name])
        return settings

    async def get_enabled_names(self, group_id: int) -> set[str]:
        settings = await self.get_all(group_id)
        return {name for name, enabled in settings.items() if enabled}

    async def toggle(self, group_id: int, prayer_name: str) -> bool:
        stmt = (
            sa.update(GroupPrayerSetting)
            .where(
                GroupPrayerSetting.group_id == group_id,
                GroupPrayerSetting.prayer_name == prayer_name,
            )
            .values(enabled=sa.not_(GroupPrayerSetting.enabled))
            .returning(GroupPrayerSetting.enabled)
        )
        result = await self._session.scalar(stmt)
        if result is None:
            raise ValueError(f"No prayer setting row for group_id={group_id} prayer_name={prayer_name}")
        return result
