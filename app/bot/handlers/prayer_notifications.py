from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.prayer_toggle import PrayerToggleCallback, prayer_toggle_keyboard
from app.database.models.group import Group
from app.database.repositories.group_prayer_setting_repository import GroupPrayerSettingRepository

router = Router(name="prayer_notifications")

TITLE = "🔔 Уведомления о джамаат-намазе\nВыберите, перед какими намазами отправлять уведомление и создавать опрос."
LOCATION_REQUIRED_TEXT = "📍 Сначала настройте местоположение группы: /set_location"


@router.message(Command("prayer_notifications"))
async def handle_prayer_notifications(message: Message, group: Group, session: AsyncSession) -> None:
    if not group.has_location:
        await message.answer(LOCATION_REQUIRED_TEXT)
        return
    settings = await GroupPrayerSettingRepository(session).get_all(group.id)
    await message.answer(TITLE, reply_markup=prayer_toggle_keyboard(settings))


@router.callback_query(PrayerToggleCallback.filter())
async def handle_toggle(
    callback: CallbackQuery, callback_data: PrayerToggleCallback, group: Group, session: AsyncSession
) -> None:
    setting_repo = GroupPrayerSettingRepository(session)
    await setting_repo.toggle(group.id, callback_data.prayer_name)
    settings = await setting_repo.get_all(group.id)
    await callback.message.edit_text(TITLE, reply_markup=prayer_toggle_keyboard(settings))
    await callback.answer()
