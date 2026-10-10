from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="help")

# Single source of truth: used both for the /help text and for Telegram's
# "/" autocomplete menu (registered via bot.set_my_commands in main.py).
COMMANDS: list[tuple[str, str]] = [
    ("start", "приветствие и краткая информация о группе"),
    ("help", "список команд"),
    ("settings", "текущие настройки группы"),
    ("set_location", "настроить местоположение по геолокации"),
    ("time_to_prepare_pray", "за сколько минут до намаза присылать уведомление"),
    ("time_to_prepare_juma", "во сколько присылать уведомление о Джума"),
    ("prayer_notifications", "выбрать, для каких намазов включить уведомления"),
    ("weekday_notifications", "выбрать дни недели для уведомлений"),
    ("today_prayers", "время намазов на сегодня"),
    ("generate_group_invitation", "сгенерировать постер-приглашение с QR-кодом"),
]

HELP_TEXT = "🕌 Доступные команды:\n\n" + "\n".join(f"/{cmd} — {desc}" for cmd, desc in COMMANDS)


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    await message.answer(HELP_TEXT)
