from aiogram.types import Chat, ChatMemberUpdated, Message, TelegramObject


def extract_chat(event: TelegramObject) -> Chat | None:
    """Pulls the originating Chat out of a Message, ChatMemberUpdated, or anything
    carrying a `.message` (e.g. CallbackQuery)."""
    if isinstance(event, Message):
        return event.chat
    if isinstance(event, ChatMemberUpdated):
        return event.chat
    message = getattr(event, "message", None)
    if message is not None:
        return getattr(message, "chat", None)
    return None
