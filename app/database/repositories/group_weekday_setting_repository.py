import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.group_weekday_setting import DEFAULT_WEEKDAY_TOGGLES, GroupWeekdaySetting


class GroupWeekdaySettingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_defaults(self, group_id: int) -> None:
        stmt = pg_insert(GroupWeekdaySetting).values(
            [
                {"group_id": group_id, "weekday": weekday, "enabled": enabled}
                for weekday, enabled in DEFAULT_WEEKDAY_TOGGLES.items()
            ]
        )
        stmt = stmt.on_conflict_do_nothing(index_elements=["group_id", "weekday"])
        await self._session.execute(stmt)

    async def get_all(self, group_id: int) -> dict[int, bool]:
        stmt = sa.select(GroupWeekdaySetting.weekday, GroupWeekdaySetting.enabled).where(
            GroupWeekdaySetting.group_id == group_id
        )
        rows = await self._session.execute(stmt)
        settings = dict(rows.all())
        # Defensive default for any weekday missing a row (should not normally happen).
        for weekday, default in DEFAULT_WEEKDAY_TOGGLES.items():
            settings.setdefault(weekday, default)
        return settings

    async def is_enabled(self, group_id: int, weekday: int) -> bool:
        return (await self.get_all(group_id))[weekday]

    async def toggle(self, group_id: int, weekday: int) -> bool:
        stmt = (
            sa.update(GroupWeekdaySetting)
            .where(
                GroupWeekdaySetting.group_id == group_id,
                GroupWeekdaySetting.weekday == weekday,
            )
            .values(enabled=sa.not_(GroupWeekdaySetting.enabled))
            .returning(GroupWeekdaySetting.enabled)
        )
        result = await self._session.scalar(stmt)
        if result is None:
            raise ValueError(f"No weekday setting row for group_id={group_id} weekday={weekday}")
        return result
