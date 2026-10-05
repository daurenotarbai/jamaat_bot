import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

logger = logging.getLogger("jamaat_bot.updates")


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            logger.info(
                "Incoming message id=%s chat_id=%s user_id=%s content_type=%s location=%r venue=%r",
                event.message_id,
                event.chat.id,
                event.from_user.id if event.from_user else None,
                event.content_type,
                event.location,
                event.venue,
            )
        else:
            logger.debug("Processing update: %s", type(event).__name__)
        try:
            return await handler(event, data)
        except Exception:
            logger.exception("Unhandled error while processing %s", type(event).__name__)
            raise
