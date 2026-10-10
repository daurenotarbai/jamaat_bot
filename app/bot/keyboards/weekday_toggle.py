from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.database.models.group_weekday_setting import WEEKDAYS

WEEKDAY_LABELS: dict[int, str] = {
    0: "Понедельник",
    1: "Вторник",
    2: "Среда",
    3: "Четверг",
    4: "Пятница",
    5: "Суббота",
    6: "Воскресенье",
}


class WeekdayToggleCallback(CallbackData, prefix="weekday_toggle"):
    weekday: int


def weekday_toggle_keyboard(settings: dict[int, bool]) -> InlineKeyboardMarkup:
    def button(weekday: int) -> InlineKeyboardButton:
        mark = "✅" if settings.get(weekday) else "❌"
        return InlineKeyboardButton(
            text=f"{mark} {WEEKDAY_LABELS[weekday]}",
            callback_data=WeekdayToggleCallback(weekday=weekday).pack(),
        )

    buttons = [button(weekday) for weekday in WEEKDAYS]
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=rows)
