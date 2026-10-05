from datetime import time
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.group import Group


class GroupRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_chat_id(self, telegram_chat_id: int) -> Group | None:
        stmt = sa.select(Group).where(Group.telegram_chat_id == telegram_chat_id)
        return await self._session.scalar(stmt)

    async def get_or_create(self, telegram_chat_id: int, title: str) -> tuple[Group, bool]:
        group = await self.get_by_chat_id(telegram_chat_id)
        if group is not None:
            changed = False
            if group.title != title:
                group.title = title
                changed = True
            if not group.is_active:
                group.is_active = True
                changed = True
            if changed:
                await self._session.flush()
            return group, False

        group = Group(telegram_chat_id=telegram_chat_id, title=title)
        self._session.add(group)
        await self._session.flush()
        return group, True

    async def update_location(
        self,
        group_id: int,
        *,
        city: str,
        city_slug: str,
        latitude: Decimal | float,
        longitude: Decimal | float,
        timezone_label: str,
        utc_offset_minutes: int,
    ) -> None:
        stmt = (
            sa.update(Group)
            .where(Group.id == group_id)
            .values(
                city=city,
                city_slug=city_slug,
                latitude=latitude,
                longitude=longitude,
                timezone=timezone_label,
                utc_offset_minutes=utc_offset_minutes,
            )
        )
        await self._session.execute(stmt)

    async def update_prepare_minutes(self, group_id: int, minutes: int) -> None:
        stmt = sa.update(Group).where(Group.id == group_id).values(prepare_pray_minutes=minutes)
        await self._session.execute(stmt)

    async def update_juma_time(self, group_id: int, juma_time: time) -> None:
        stmt = sa.update(Group).where(Group.id == group_id).values(juma_notification_time=juma_time)
        await self._session.execute(stmt)

    async def deactivate(self, group_id: int) -> None:
        stmt = sa.update(Group).where(Group.id == group_id).values(is_active=False)
        await self._session.execute(stmt)

    async def get_active_with_location(self) -> list[Group]:
        stmt = sa.select(Group).where(
            Group.is_active.is_(True),
            Group.latitude.is_not(None),
            Group.longitude.is_not(None),
            Group.utc_offset_minutes.is_not(None),
        )
        result = await self._session.scalars(stmt)
        return list(result)
