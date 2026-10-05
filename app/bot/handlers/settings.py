from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.formatting import format_settings_text
from app.database.models.group import Group
from app.database.repositories.group_prayer_setting_repository import GroupPrayerSettingRepository

router = Router(name="settings")


@router.message(Command("settings"))
async def handle_settings(message: Message, group: Group, session: AsyncSession) -> None:
    prayer_settings = await GroupPrayerSettingRepository(session).get_all(group.id)
    await message.answer(format_settings_text(group, prayer_settings))
