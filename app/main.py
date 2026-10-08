import asyncio
import logging
from datetime import timedelta

import httpx
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeAllGroupChats

from app.bot.error_handler import register_error_handler
from app.bot.handlers import routers
from app.bot.handlers.help import COMMANDS as HELP_COMMANDS
from app.bot.middlewares.group_context import GroupContextMiddleware
from app.bot.middlewares.logging import LoggingMiddleware
from app.config import get_settings
from app.database.engine import create_engine, create_session_factory
from app.logging_config import configure_logging
from app.services.prayer_times import PrayerTimesService
from app.services.scheduler import SchedulerService

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    engine = create_engine(settings)
    session_factory = create_session_factory(engine)

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await bot.set_my_commands(
        [BotCommand(command=cmd, description=desc) for cmd, desc in HELP_COMMANDS],
        scope=BotCommandScopeAllGroupChats(),
    )
    dp = Dispatcher(storage=MemoryStorage())
    register_error_handler(dp, bot)

    group_context_mw = GroupContextMiddleware(session_factory, admin_user_id=settings.admin_user_id)
    logging_mw = LoggingMiddleware()
    for observer in (dp.message, dp.callback_query, dp.my_chat_member):
        observer.outer_middleware(logging_mw)
        observer.outer_middleware(group_context_mw)

    for router in routers:
        dp.include_router(router)

    http_client = httpx.AsyncClient(timeout=15.0)
    prayer_times_service = PrayerTimesService(http_client, settings.dumk_api_base_url)
    warm_up_task = asyncio.create_task(_warm_up_cities_cache(prayer_times_service))

    scheduler_service = SchedulerService(
        bot=bot,
        session_factory=session_factory,
        prayer_times_service=prayer_times_service,
        tick_seconds=settings.scheduler_tick_seconds,
        stale_threshold=timedelta(minutes=settings.notification_stale_threshold_minutes),
        horizon_days=settings.schedule_horizon_days,
        refresh_interval_hours=settings.schedule_refresh_interval_hours,
    )
    scheduler_service.start()

    try:
        await dp.start_polling(
            bot, prayer_times_service=prayer_times_service, settings=settings, session_factory=session_factory
        )
    finally:
        warm_up_task.cancel()
        await scheduler_service.shutdown()
        await http_client.aclose()
        await engine.dispose()
        await bot.session.close()


async def _warm_up_cities_cache(prayer_times_service: PrayerTimesService) -> None:
    """Pre-fetches the (paginated, ~60-request) DUMK city list at startup so the first
    /set_location in any group doesn't have to pay that cost itself."""
    try:
        cities = await prayer_times_service.get_cities()
        logger.info("Warmed up DUMK city list cache: %d cities", len(cities))
    except Exception:
        logger.exception("Failed to warm up DUMK city list cache; will retry on first /set_location")


if __name__ == "__main__":
    asyncio.run(main())
