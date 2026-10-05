from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states import PreparePrayFlow
from app.database.models.group import Group
from app.database.repositories.group_repository import GroupRepository
from app.services.validation import validate_minutes

router = Router(name="prayer_settings")

ASK_TEXT = "⏰ За сколько минут до начала намаза отправлять уведомление?"


@router.message(Command("time_to_prepare_pray"))
async def handle_time_to_prepare_pray(message: Message, state: FSMContext) -> None:
    await state.set_state(PreparePrayFlow.waiting_for_minutes)
    await message.answer(ASK_TEXT)


@router.message(PreparePrayFlow.waiting_for_minutes)
async def handle_minutes_input(
    message: Message, state: FSMContext, group: Group, session: AsyncSession
) -> None:
    try:
        minutes = validate_minutes(message.text or "")
    except ValueError as exc:
        await message.answer(f"⚠️ {exc}")
        return

    await GroupRepository(session).update_prepare_minutes(group.id, minutes)
    await state.clear()
    await message.answer(
        "✅ Готово.\n"
        f"Теперь уведомление будет отправляться за {minutes} минут до начала выбранных намазов."
    )
