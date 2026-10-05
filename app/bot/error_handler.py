import logging

from aiogram import Bot, Dispatcher
from aiogram.types import ErrorEvent

from app.bot.chat_utils import extract_chat

logger = logging.getLogger(__name__)

GENERIC_ERROR_TEXT = (
    "⚠️ Произошла непредвиденная ошибка при обработке запроса. Попробуйте, пожалуйста, ещё раз."
)

# Update fields that can carry an inner event with a chat -- checked in order.
_UPDATE_EVENT_FIELDS = ("message", "edited_message", "channel_post", "my_chat_member", "callback_query")


def register_error_handler(dp: Dispatcher, bot: Bot) -> None:
    """Safety net so a bug never leaves the group in total silence (per spec: every
    error must be reported in the group chat, never swallowed)."""

    async def handle_unexpected_error(event: ErrorEvent) -> None:
        logger.exception("Unhandled error while processing update", exc_info=event.exception)

        chat = None
        for field in _UPDATE_EVENT_FIELDS:
            inner_event = getattr(event.update, field, None)
            if inner_event is not None:
                chat = extract_chat(inner_event)
                if chat is not None:
                    break

        if chat is not None and chat.type != "private":
            try:
                await bot.send_message(chat.id, GENERIC_ERROR_TEXT)
            except Exception:
                logger.exception("Failed to notify chat_id=%s about an internal error", chat.id)

    dp.errors.register(handle_unexpected_error)
