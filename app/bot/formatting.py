from app.database.models.group import Group
from app.database.models.prayer_schedule import PRAYER_NAMES
from app.services.scheduler import PRAYER_LABELS
from app.services.timezone import format_offset_label


def format_settings_text(group: Group, prayer_settings: dict[str, bool]) -> str:
    if not group.has_location:
        return (
            "⚙️ Настройки группы\n\n"
            "📍 Место: не настроено\n\n"
            "Используйте /set_location"
        )

    toggles_lines = "\n".join(
        f"{'✅' if prayer_settings.get(name) else '❌'} {PRAYER_LABELS[name]}" for name in PRAYER_NAMES
    )
    offset_label = format_offset_label(group.utc_offset_minutes) if group.utc_offset_minutes is not None else "—"
    juma_time = group.juma_notification_time.strftime("%H:%M")

    return (
        "⚙️ Настройки группы\n\n"
        f"📍 Место: {group.city}\n"
        f"🌍 Timezone: {offset_label}\n\n"
        "🔔 Уведомления:\n"
        f"{toggles_lines}\n\n"
        f"⏰ За: {group.prepare_pray_minutes} минут\n\n"
        f"🕌 Джума: {juma_time}"
    )
