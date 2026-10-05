from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.formatting import format_settings_text
from app.database.models.group import Group
from app.database.repositories.group_prayer_setting_repository import GroupPrayerSettingRepository

router = Router(name="start")

WELCOME_TEXT = (
    "🕌 Добро пожаловать!\n"
    "Я помогу организовать джамаат-намаз в этой группе.\n\n"
    "Сначала необходимо настроить местоположение группы.\n"
    "Используйте:\n"
    "/set_location\n\n"
    "После настройки будут доступны уведомления о намазах и опросы участников."
)


@router.message(Command("start"))
async def handle_start(message: Message, group: Group, session: AsyncSession) -> None:
    if not group.has_location:
        await message.answer(WELCOME_TEXT)
        return

    prayer_settings = await GroupPrayerSettingRepository(session).get_all(group.id)
    await message.answer(format_settings_text(group, prayer_settings))
