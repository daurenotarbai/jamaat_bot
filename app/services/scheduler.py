import logging
from datetime import date, datetime, time, timedelta
from datetime import timezone as dt_timezone
from typing import Literal

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.database.models.group import Group
from app.database.models.poll import JUMA_SENTINEL
from app.database.models.prayer_schedule import PrayerSchedule
from app.database.repositories.group_prayer_setting_repository import GroupPrayerSettingRepository
from app.database.repositories.group_repository import GroupRepository
from app.database.repositories.poll_repository import PollRepository
from app.database.repositories.prayer_schedule_repository import PrayerScheduleRepository
from app.services.prayer_times import PrayerTimesService, ensure_schedule_cached
from app.services.timezone import offset_to_tzinfo

logger = logging.getLogger(__name__)

PRAYER_LABELS: dict[str, str] = {
    "fajr": "Фаджр",
    "zuhr": "Зухр",
    "asr": "Аср",
    "maghrib": "Магриб",
    "isha": "Иша",
}

POLL_OPTIONS = ["🙋 Буду", "❌ Не буду", "❓ Пока не знаю"]

Decision = Literal["skip_not_due", "send", "skip_stale", "skip_already_sent"]


# ---- Pure, unit-testable decision functions ------------------------------------------


def compute_notify_at(
    prayer_date: date, prayer_time: time, utc_offset_minutes: int, prepare_minutes: int
) -> datetime:
    local_dt = datetime.combine(prayer_date, prayer_time, tzinfo=offset_to_tzinfo(utc_offset_minutes))
    return (local_dt - timedelta(minutes=prepare_minutes)).astimezone(dt_timezone.utc)


def is_stale(now: datetime, notify_at: datetime, threshold: timedelta) -> bool:
    return (now - notify_at) > threshold


def should_send(now: datetime, notify_at: datetime, notification_sent: bool, stale_threshold: timedelta) -> Decision:
    if notification_sent:
        return "skip_already_sent"
    if now < notify_at:
        return "skip_not_due"
    if is_stale(now, notify_at, stale_threshold):
        return "skip_stale"
    return "send"


def is_juma_due(now_local: datetime, juma_time: time, grace: timedelta) -> bool:
    due_at = now_local.replace(
        hour=juma_time.hour, minute=juma_time.minute, second=0, microsecond=0
    )
    return due_at <= now_local <= due_at + grace


# ---- Scheduler service -----------------------------------------------------------------


class SchedulerService:
    def __init__(
        self,
        *,
        bot: Bot,
        session_factory: async_sessionmaker[AsyncSession],
        prayer_times_service: PrayerTimesService,
        tick_seconds: int,
        stale_threshold: timedelta,
        horizon_days: int,
        refresh_interval_hours: int,
    ) -> None:
        self._bot = bot
        self._session_factory = session_factory
        self._prayer_times_service = prayer_times_service
        self._stale_threshold = stale_threshold
        self._horizon_days = horizon_days
        self._scheduler = AsyncIOScheduler()
        self._tick_seconds = tick_seconds
        self._refresh_interval_hours = refresh_interval_hours

    def start(self) -> None:
        self._scheduler.add_job(
            self._tick_notifications,
            trigger=IntervalTrigger(seconds=self._tick_seconds),
            id="tick_notifications",
            coalesce=True,
            max_instances=1,
            next_run_time=datetime.now(dt_timezone.utc),
        )
        self._scheduler.add_job(
            self._refresh_schedules,
            trigger=IntervalTrigger(hours=self._refresh_interval_hours),
            id="refresh_schedules",
            coalesce=True,
            max_instances=1,
            next_run_time=datetime.now(dt_timezone.utc),
        )
        self._scheduler.start()

    async def shutdown(self) -> None:
        self._scheduler.shutdown(wait=False)

    async def _tick_notifications(self) -> None:
        now_utc = datetime.now(dt_timezone.utc)
        async with self._session_factory() as session:
            groups = await GroupRepository(session).get_active_with_location()

        for group in groups:
            try:
                await self._process_group(group, now_utc)
            except Exception:
                logger.exception("Failed processing notifications for group_id=%s", group.id)

    async def _process_group(self, group: Group, now_utc: datetime) -> None:
        tzinfo = offset_to_tzinfo(group.utc_offset_minutes)
        local_now = now_utc.astimezone(tzinfo)
        today = local_now.date()

        async with self._session_factory() as session:
            schedule_repo = PrayerScheduleRepository(session)
            setting_repo = GroupPrayerSettingRepository(session)

            enabled = await setting_repo.get_enabled_names(group.id)
            pending = await schedule_repo.get_pending_for_date(group.id, today)

            for row in pending:
                if row.prayer_name not in enabled:
                    continue
                await self._maybe_send_prayer(session, group, row, now_utc)

            if local_now.weekday() == 4:  # Friday
                await self._maybe_send_juma(session, group, today, local_now)

            await session.commit()

    async def _maybe_send_prayer(
        self,
        session: AsyncSession,
        group: Group,
        row: PrayerSchedule,
        now_utc: datetime,
    ) -> None:
        notify_at = compute_notify_at(row.date, row.prayer_time, group.utc_offset_minutes, group.prepare_pray_minutes)
        decision = should_send(now_utc, notify_at, row.notification_sent, self._stale_threshold)

        if decision in ("skip_not_due", "skip_already_sent"):
            return

        schedule_repo = PrayerScheduleRepository(session)
        if decision == "skip_stale":
            await schedule_repo.mark_sent_skip(row.id)
            logger.info(
                "Skipped stale notification group_id=%s prayer=%s date=%s", group.id, row.prayer_name, row.date
            )
            return

        claimed = await schedule_repo.try_claim(row.id)
        if not claimed:
            return

        label = PRAYER_LABELS[row.prayer_name]
        try:
            await self._bot.send_message(
                group.telegram_chat_id,
                f"🕌 Скоро {label}\nНачало намаза: {row.prayer_time.strftime('%H:%M')}\n"
                "Кто будет совершать намаз с джамаатом?",
            )
            poll_message = await self._bot.send_poll(
                group.telegram_chat_id,
                question=f"🕌 Кто будет на {label}?",
                options=POLL_OPTIONS,
                is_anonymous=False,
            )
        except TelegramForbiddenError:
            await GroupRepository(session).deactivate(group.id)
            return
        except TelegramRetryAfter:
            logger.warning("Rate limited sending notification to group_id=%s", group.id)
            return

        await PollRepository(session).create(
            group_id=group.id,
            day=row.date,
            poll_type="prayer",
            prayer_name=row.prayer_name,
            telegram_message_id=poll_message.message_id,
            telegram_poll_id=poll_message.poll.id,
        )

    async def _maybe_send_juma(
        self, session: AsyncSession, group: Group, today: date, local_now: datetime
    ) -> None:
        if not is_juma_due(local_now, group.juma_notification_time, self._stale_threshold):
            return

        poll_repo = PollRepository(session)
        if await poll_repo.exists(group.id, today, "juma", JUMA_SENTINEL):
            return

        try:
            await self._bot.send_message(
                group.telegram_chat_id,
                "🕌 Джума\nСегодня пятничный намаз.\nКто будет на Джума?",
            )
            poll_message = await self._bot.send_poll(
                group.telegram_chat_id,
                question="🕌 Кто будет на Джума?",
                options=POLL_OPTIONS,
                is_anonymous=False,
            )
        except TelegramForbiddenError:
            await GroupRepository(session).deactivate(group.id)
            return
        except TelegramRetryAfter:
            logger.warning("Rate limited sending juma notification to group_id=%s", group.id)
            return

        await poll_repo.create(
            group_id=group.id,
            day=today,
            poll_type="juma",
            prayer_name=JUMA_SENTINEL,
            telegram_message_id=poll_message.message_id,
            telegram_poll_id=poll_message.poll.id,
        )

    async def _refresh_schedules(self) -> None:
        async with self._session_factory() as session:
            groups = await GroupRepository(session).get_active_with_location()

        today = datetime.now(dt_timezone.utc).date()
        for group in groups:
            async with self._session_factory() as session:
                schedule_repo = PrayerScheduleRepository(session)
                try:
                    await ensure_schedule_cached(
                        group_id=group.id,
                        latitude=float(group.latitude),
                        longitude=float(group.longitude),
                        schedule_repo=schedule_repo,
                        prayer_times_service=self._prayer_times_service,
                        today=today,
                        horizon_days=self._horizon_days,
                    )
                    await session.commit()
                except Exception:
                    logger.exception("Failed to refresh schedule cache for group_id=%s", group.id)
