import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot
from aiogram.types import Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.chat_utils import extract_chat
from app.database.repositories.group_prayer_setting_repository import GroupPrayerSettingRepository
from app.database.repositories.group_weekday_setting_repository import GroupWeekdaySettingRepository
from app.database.repositories.group_repository import GroupRepository
from app.database.repositories.private_user_repository import PrivateUserRepository

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

    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], admin_user_id: int | None = None
    ) -> None:
        self._session_factory = session_factory
        self._admin_user_id = admin_user_id

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
            if self._is_admin_stats(event):
                return await handler(event, data)
            if isinstance(event, Message):
                await self._record_private_user(event)
                bot: Bot = data["bot"]
                await bot.send_message(chat.id, _PRIVATE_CHAT_NOTICE)
            return None

        async with self._session_factory() as session:
            group_repo = GroupRepository(session)
            group, created = await group_repo.get_or_create(chat.id, chat.title or str(chat.id))
            if created:
                await GroupPrayerSettingRepository(session).create_defaults(group.id)
                await GroupWeekdaySettingRepository(session).create_defaults(group.id)
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

    def _is_admin_stats(self, event: TelegramObject) -> bool:
        """The owner's /stats is the only thing allowed through in a private chat."""
        if not isinstance(event, Message) or self._admin_user_id is None or event.from_user is None:
            return False
        text = event.text or ""
        return event.from_user.id == self._admin_user_id and text.split("@")[0].split()[:1] == ["/stats"]

    async def _record_private_user(self, message: Message) -> None:
        """Best-effort usage stats: a DB failure here must never block the private-chat notice."""
        user = message.from_user
        if user is None:
            return
        try:
            async with self._session_factory() as session:
                await PrivateUserRepository(session).record_seen(user.id, user.username, user.first_name)
                await session.commit()
        except Exception:
            logger.exception("Failed to record private user_id=%s", user.id)
