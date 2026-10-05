from datetime import date, time

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.prayer_schedule import PrayerSchedule


class PrayerScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_batch(self, group_id: int, rows: list[tuple[date, str, time]]) -> None:
        if not rows:
            return
        values = [
            {"group_id": group_id, "date": day, "prayer_name": prayer_name, "prayer_time": prayer_time}
            for day, prayer_name, prayer_time in rows
        ]
        stmt = pg_insert(PrayerSchedule).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=["group_id", "date", "prayer_name"],
            set_={"prayer_time": stmt.excluded.prayer_time},
        )
        await self._session.execute(stmt)

    async def get_pending_for_date(self, group_id: int, day: date) -> list[PrayerSchedule]:
        stmt = sa.select(PrayerSchedule).where(
            PrayerSchedule.group_id == group_id,
            PrayerSchedule.date == day,
            PrayerSchedule.notification_sent.is_(False),
        )
        result = await self._session.scalars(stmt)
        return list(result)

    async def get_for_date(self, group_id: int, day: date) -> list[PrayerSchedule]:
        stmt = sa.select(PrayerSchedule).where(PrayerSchedule.group_id == group_id, PrayerSchedule.date == day)
        result = await self._session.scalars(stmt)
        return list(result)

    async def try_claim(self, schedule_id: int) -> bool:
        stmt = (
            sa.update(PrayerSchedule)
            .where(PrayerSchedule.id == schedule_id, PrayerSchedule.notification_sent.is_(False))
            .values(notification_sent=True)
            .returning(PrayerSchedule.id)
        )
        result = await self._session.scalar(stmt)
        return result is not None

    async def mark_sent_skip(self, schedule_id: int) -> None:
        stmt = (
            sa.update(PrayerSchedule)
            .where(PrayerSchedule.id == schedule_id, PrayerSchedule.notification_sent.is_(False))
            .values(notification_sent=True)
        )
        await self._session.execute(stmt)

    async def coverage_range(self, group_id: int) -> tuple[date | None, date | None]:
        stmt = sa.select(sa.func.min(PrayerSchedule.date), sa.func.max(PrayerSchedule.date)).where(
            PrayerSchedule.group_id == group_id
        )
        result = await self._session.execute(stmt)
        min_date, max_date = result.one()
        return min_date, max_date

    async def delete_future(self, group_id: int, from_date: date) -> None:
        stmt = sa.delete(PrayerSchedule).where(
            PrayerSchedule.group_id == group_id, PrayerSchedule.date >= from_date
        )
        await self._session.execute(stmt)
