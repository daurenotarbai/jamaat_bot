from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.weekday_toggle import WeekdayToggleCallback, weekday_toggle_keyboard
from app.database.models.group import Group
from app.database.repositories.group_weekday_setting_repository import GroupWeekdaySettingRepository

router = Router(name="weekday_notifications")

TITLE = "📅 Дни недели для уведомлений\nВыберите, в какие дни отправлять уведомления и создавать опросы о джамаат-намазе."
LOCATION_REQUIRED_TEXT = "📍 Сначала настройте местоположение группы: /set_location"


@router.message(Command("weekday_notifications"))
async def handle_weekday_notifications(message: Message, group: Group, session: AsyncSession) -> None:
    if not group.has_location:
        await message.answer(LOCATION_REQUIRED_TEXT)
        return
    settings = await GroupWeekdaySettingRepository(session).get_all(group.id)
    await message.answer(TITLE, reply_markup=weekday_toggle_keyboard(settings))


@router.callback_query(WeekdayToggleCallback.filter())
async def handle_toggle(
    callback: CallbackQuery, callback_data: WeekdayToggleCallback, group: Group, session: AsyncSession
) -> None:
    setting_repo = GroupWeekdaySettingRepository(session)
    await setting_repo.toggle(group.id, callback_data.weekday)
    settings = await setting_repo.get_all(group.id)
    await callback.message.edit_text(TITLE, reply_markup=weekday_toggle_keyboard(settings))
    await callback.answer()
