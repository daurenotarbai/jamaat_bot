import logging
from datetime import UTC, datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.models.group import Group
from app.database.models.prayer_schedule import PRAYER_NAMES
from app.database.repositories.prayer_schedule_repository import PrayerScheduleRepository
from app.services.prayer_times import (
    PrayerTimesAPIError,
    PrayerTimesParseError,
    PrayerTimesService,
    ensure_schedule_cached,
)
from app.services.scheduler import PRAYER_LABELS
from app.services.timezone import offset_to_tzinfo

logger = logging.getLogger(__name__)

router = Router(name="prayer_times")

LOCATION_REQUIRED_TEXT = "📍 Сначала настройте местоположение группы: /set_location"
UNAVAILABLE_TEXT = "😕 Не удалось получить время намазов. Попробуйте позже."


@router.message(Command("today_prayers"))
async def handle_today_prayers(
    message: Message,
    group: Group,
    session: AsyncSession,
    prayer_times_service: PrayerTimesService,
    settings: Settings,
) -> None:
    if not group.has_location:
        await message.answer(LOCATION_REQUIRED_TEXT)
        return

    today = datetime.now(UTC).astimezone(offset_to_tzinfo(group.utc_offset_minutes)).date()
    schedule_repo = PrayerScheduleRepository(session)

    rows = await schedule_repo.get_for_date(group.id, today)
    if not rows:
        try:
            await ensure_schedule_cached(
                group_id=group.id,
                latitude=float(group.latitude),
                longitude=float(group.longitude),
                schedule_repo=schedule_repo,
                prayer_times_service=prayer_times_service,
                today=today,
                horizon_days=settings.schedule_horizon_days,
            )
        except (PrayerTimesAPIError, PrayerTimesParseError):
            logger.exception("Failed to fetch prayer schedule for group_id=%s", group.id)
        rows = await schedule_repo.get_for_date(group.id, today)

    if not rows:
        await message.answer(UNAVAILABLE_TEXT)
        return

    times = {row.prayer_name: row.prayer_time for row in rows}
    lines = "\n".join(
        f"{PRAYER_LABELS[name]} — {times[name].strftime('%H:%M')}" for name in PRAYER_NAMES if name in times
    )
    await message.answer(f"🕌 Время намазов на сегодня ({today:%d.%m.%Y})\n📍 {group.city}\n\n{lines}")
