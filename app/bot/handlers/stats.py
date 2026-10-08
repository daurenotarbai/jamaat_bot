from datetime import UTC, datetime, timedelta

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings
from app.database.repositories.group_repository import GroupRepository
from app.database.repositories.private_user_repository import PrivateUserRepository

router = Router(name="stats")


@router.message(Command("stats"))
async def handle_stats(
    message: Message, settings: Settings, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    # Not listed in /help on purpose: this is an owner-only command and stays silent for everyone else.
    if settings.admin_user_id is None or message.from_user is None or message.from_user.id != settings.admin_user_id:
        return

    now = datetime.now(UTC)
    async with session_factory() as session:
        users = PrivateUserRepository(session)
        total_users = await users.count()
        week_users = await users.count_seen_since(now - timedelta(days=7))
        total_groups, active_groups, with_location = await GroupRepository(session).count_stats()

    await message.answer(
        "📊 Статистика бота\n\n"
        f"👤 Писали боту в личку: {total_users}\n"
        f"   за 7 дней: {week_users}\n\n"
        f"👥 Групп всего: {total_groups}\n"
        f"✅ Активных: {active_groups}\n"
        f"📍 С настроенным городом: {with_location}"
    )
