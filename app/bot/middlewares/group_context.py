import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot
from aiogram.types import Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.chat_utils import extract_chat
from app.database.repositories.group_prayer_setting_repository import GroupPrayerSettingRepository
from app.database.repositories.group_repository import GroupRepository

logger = logging.getLogger(__name__)

_PRIVATE_CHAT_NOTICE = (
    "🕌 Я работаю только внутри групповых чатов.\n"
    "Добавьте меня в группу, чтобы организовать джамаат-намаз."
)


class GroupContextMiddleware(BaseMiddleware):
    """Blocks all private-chat interactions and injects `group`/`session` for group chats.

    Any group member can change settings (no admin checks, per spec), so this middleware
    just needs a group row to exist -- it is created on first contact with sensible
    defaults (including the default prayer-notification toggles).
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        chat = extract_chat(event)
        if chat is None:
            return await handler(event, data)

        if chat.type == "private":
            if isinstance(event, Message):
                bot: Bot = data["bot"]
                await bot.send_message(chat.id, _PRIVATE_CHAT_NOTICE)
            return None

        async with self._session_factory() as session:
            group_repo = GroupRepository(session)
            group, created = await group_repo.get_or_create(chat.id, chat.title or str(chat.id))
            if created:
                await GroupPrayerSettingRepository(session).create_defaults(group.id)
            await session.commit()

            data["session"] = session
            data["group"] = group
            try:
                result = await handler(event, data)
            except Exception:
                await session.rollback()
                raise
            await session.commit()
            return result
