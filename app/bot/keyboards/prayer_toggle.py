from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.database.models.prayer_schedule import PRAYER_NAMES
from app.services.scheduler import PRAYER_LABELS


class PrayerToggleCallback(CallbackData, prefix="prayer_toggle"):
    prayer_name: str


def prayer_toggle_keyboard(settings: dict[str, bool]) -> InlineKeyboardMarkup:
    def button(name: str) -> InlineKeyboardButton:
        mark = "✅" if settings.get(name) else "❌"
        return InlineKeyboardButton(
            text=f"{mark} {PRAYER_LABELS[name]}",
            callback_data=PrayerToggleCallback(prayer_name=name).pack(),
        )

    fajr, zuhr, asr, maghrib, isha = (button(name) for name in PRAYER_NAMES)
    return InlineKeyboardMarkup(inline_keyboard=[[fajr, zuhr], [asr, maghrib], [isha]])
