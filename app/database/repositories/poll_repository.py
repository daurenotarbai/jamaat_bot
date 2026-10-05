from datetime import date

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.poll import Poll


class PollRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def exists(self, group_id: int, day: date, poll_type: str, prayer_name: str) -> bool:
        stmt = sa.select(sa.literal(True)).where(
            Poll.group_id == group_id,
            Poll.date == day,
            Poll.type == poll_type,
            Poll.prayer_name == prayer_name,
        )
        return (await self._session.scalar(stmt)) is not None

    async def create(
        self,
        *,
        group_id: int,
        day: date,
        poll_type: str,
        prayer_name: str,
        telegram_message_id: int,
        telegram_poll_id: str,
    ) -> bool:
        """Returns True if the poll row was created, False if it already existed (race-safe)."""
        poll = Poll(
            group_id=group_id,
            date=day,
            type=poll_type,
            prayer_name=prayer_name,
            telegram_message_id=telegram_message_id,
            telegram_poll_id=telegram_poll_id,
        )
        try:
            # A savepoint, not the outer transaction, is rolled back on conflict -- this
            # runs inside the same unit of work as the schedule-row claim and must not
            # undo it if the poll insert loses a race.
            async with self._session.begin_nested():
                self._session.add(poll)
                await self._session.flush()
        except IntegrityError:
            return False
        return True
