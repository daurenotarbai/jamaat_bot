import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from app.database.models.group import Group
from app.services.invitation import InsufficientRightsError, compose_poster, generate_qr_code, get_or_create_invite_link

logger = logging.getLogger(__name__)
router = Router(name="invitation")

RIGHTS_ERROR_TEXT = (
    "❌ Не удалось получить ссылку-приглашение.\n"
    "Возможно, боту необходимы права администратора для создания invite link."
)
CAPTION = "Вы можете распечатать этот QR-код и разместить его в намазхане, чтобы другие могли легко присоединиться."


@router.message(Command("generate_group_invitation"))
async def handle_generate_invitation(message: Message, group: Group, bot: Bot) -> None:
    try:
        invite_link = await get_or_create_invite_link(bot, group.telegram_chat_id)
    except InsufficientRightsError:
        logger.warning("Insufficient rights to export invite link for group_id=%s", group.id)
        await message.answer(RIGHTS_ERROR_TEXT)
        return

    bot_user = await bot.me()
    qr_image = generate_qr_code(invite_link)
    poster_bytes = compose_poster(qr_image, group.title, bot_user.username)
    # Sent as a document, not a photo: sendPhoto recompresses to JPEG and downsizes,
    # which blurs the QR code and text -- unacceptable for a poster meant to be printed.
    await message.answer_document(
        BufferedInputFile(poster_bytes, filename="invitation.png"),
        caption=CAPTION,
    )
