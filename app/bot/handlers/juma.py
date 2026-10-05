from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.states import JumaTimeFlow
from app.database.models.group import Group
from app.database.repositories.group_repository import GroupRepository
from app.services.validation import validate_time_hhmm

router = Router(name="juma")

ASK_TEXT = "🕌 Во сколько отправлять уведомление о Джума?"


@router.message(Command("time_to_prepare_juma"))
async def handle_time_to_prepare_juma(message: Message, state: FSMContext) -> None:
    await state.set_state(JumaTimeFlow.waiting_for_time)
    await message.answer(ASK_TEXT)


@router.message(JumaTimeFlow.waiting_for_time)
async def handle_juma_time_input(
    message: Message, state: FSMContext, group: Group, session: AsyncSession
) -> None:
    try:
        juma_time = validate_time_hhmm(message.text or "")
    except ValueError as exc:
        await message.answer(f"⚠️ {exc}")
        return

    await GroupRepository(session).update_juma_time(group.id, juma_time)
    await state.clear()
    await message.answer(
        "✅ Готово.\n"
        f"Каждую пятницу уведомление о Джума будет отправляться в {juma_time.strftime('%H:%M')}."
    )
