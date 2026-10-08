import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.private_user import PrivateUser


class PrivateUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record_seen(self, telegram_user_id: int, username: str | None, first_name: str | None) -> None:
        stmt = pg_insert(PrivateUser).values(
            telegram_user_id=telegram_user_id, username=username, first_name=first_name
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["telegram_user_id"],
            set_={"username": stmt.excluded.username, "first_name": stmt.excluded.first_name, "last_seen_at": sa.func.now()},
        )
        await self._session.execute(stmt)

    async def count(self) -> int:
        return await self._session.scalar(sa.select(sa.func.count()).select_from(PrivateUser)) or 0
