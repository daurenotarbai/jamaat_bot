import logging
from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.city_picker import (
    CityPageCallback,
    CitySelectCallback,
    ConfirmCityCallback,
    city_list_keyboard,
    confirm_city_keyboard,
)
from app.bot.states import LocationFlow
from app.config import Settings
from app.database.models.group import Group
from app.database.repositories.group_repository import GroupRepository
from app.database.repositories.prayer_schedule_repository import PrayerScheduleRepository
from app.services.location import find_nearest_city, is_within_threshold
from app.services.prayer_times import (
    City,
    PrayerTimesAPIError,
    PrayerTimesParseError,
    PrayerTimesService,
    ensure_schedule_cached,
)
from app.services.timezone import format_offset_label

logger = logging.getLogger(__name__)
router = Router(name="location")

ASK_LOCATION_TEXT = "📍 Отправьте вашу геолокацию, чтобы определить место для расчёта времени намаза."
NOT_A_LOCATION_TEXT = (
    "⚠️ Это не похоже на геолокацию. Пожалуйста, воспользуйтесь функцией Telegram "
    "«Отправить геопозицию» (📎 → Location)."
)
API_DOWN_TEXT = "⚠️ Сервис расписания намазов ДУМК временно недоступен. Попробуйте, пожалуйста, позже."
CITY_NOT_FOUND_TEXT = "Город не найден, попробуйте снова: /set_location"


@router.message(Command("set_location"))
async def handle_set_location(message: Message, state: FSMContext) -> None:
    await state.set_state(LocationFlow.waiting_for_location)
    await message.answer(ASK_LOCATION_TEXT)


@router.message(LocationFlow.waiting_for_location, F.location)
async def handle_location_message(
    message: Message,
    state: FSMContext,
    prayer_times_service: PrayerTimesService,
    settings: Settings,
) -> None:
    lat, lng = message.location.latitude, message.location.longitude
    try:
        cities = await prayer_times_service.get_cities()
    except (PrayerTimesAPIError, PrayerTimesParseError):
        logger.exception("Failed to fetch DUMK city list")
        await message.answer(API_DOWN_TEXT)
        return

    city, distance_km = find_nearest_city(cities, lat, lng)
    await state.update_data(cities=[_city_to_dict(c) for c in cities])

    if is_within_threshold(distance_km, settings.nearest_city_threshold_km):
        await message.answer(
            "📍 Определён город:\n"
            f"{city.title}\n\n"
            "Координаты:\n"
            f"{lat:.4f}, {lng:.4f}\n\n"
            "Использовать это местоположение для времени намаза?",
            reply_markup=confirm_city_keyboard(city.slug),
        )
        return

    await message.answer(
        "📍 Не удалось автоматически определить ближайший город (он слишком далеко).\n"
        "Пожалуйста, выберите город из списка:",
        reply_markup=city_list_keyboard(cities, page=0),
    )


@router.message(LocationFlow.waiting_for_location)
async def handle_location_wrong_content(message: Message) -> None:
    await message.answer(NOT_A_LOCATION_TEXT)


@router.message(F.location)
async def handle_unexpected_location(message: Message) -> None:
    """A location can arrive with no active flow -- e.g. the bot process restarted
    (in-memory FSM storage) between /set_location and the user sharing it. Report that
    in the group instead of silently ignoring the message."""
    await message.answer(
        "📍 Я не ожидал геолокацию прямо сейчас (возможно, бот перезапускался).\n"
        "Выполните /set_location и отправьте её ещё раз."
    )


@router.callback_query(LocationFlow.waiting_for_location, ConfirmCityCallback.filter(F.answer == "no"))
async def handle_city_rejected(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    cities = [_city_from_dict(c) for c in data.get("cities", [])]
    await callback.message.edit_text(
        "📍 Пожалуйста, выберите город из списка:", reply_markup=city_list_keyboard(cities, page=0)
    )
    await callback.answer()


@router.callback_query(LocationFlow.waiting_for_location, ConfirmCityCallback.filter(F.answer == "yes"))
async def handle_city_confirmed(
    callback: CallbackQuery,
    callback_data: ConfirmCityCallback,
    state: FSMContext,
    group: Group,
    session: AsyncSession,
    prayer_times_service: PrayerTimesService,
    settings: Settings,
) -> None:
    data = await state.get_data()
    cities = [_city_from_dict(c) for c in data.get("cities", [])]
    city = next((c for c in cities if c.slug == callback_data.slug), None)
    if city is None:
        await callback.answer(CITY_NOT_FOUND_TEXT, show_alert=True)
        return

    await _save_location_and_refresh(
        session=session,
        group=group,
        city=city,
        prayer_times_service=prayer_times_service,
        horizon_days=settings.schedule_horizon_days,
    )
    await state.clear()
    await callback.message.edit_text(f"✅ Местоположение сохранено: {city.title}")
    await callback.answer()


@router.callback_query(LocationFlow.waiting_for_location, CityPageCallback.filter())
async def handle_city_page(callback: CallbackQuery, callback_data: CityPageCallback, state: FSMContext) -> None:
    data = await state.get_data()
    cities = [_city_from_dict(c) for c in data.get("cities", [])]
    await callback.message.edit_reply_markup(reply_markup=city_list_keyboard(cities, page=callback_data.page))
    await callback.answer()


@router.callback_query(LocationFlow.waiting_for_location, CitySelectCallback.filter())
async def handle_city_selected(
    callback: CallbackQuery,
    callback_data: CitySelectCallback,
    state: FSMContext,
    group: Group,
    session: AsyncSession,
    prayer_times_service: PrayerTimesService,
    settings: Settings,
) -> None:
    data = await state.get_data()
    cities = [_city_from_dict(c) for c in data.get("cities", [])]
    city = next((c for c in cities if c.slug == callback_data.slug), None)
    if city is None:
        await callback.answer(CITY_NOT_FOUND_TEXT, show_alert=True)
        return

    await _save_location_and_refresh(
        session=session,
        group=group,
        city=city,
        prayer_times_service=prayer_times_service,
        horizon_days=settings.schedule_horizon_days,
    )
    await state.clear()
    await callback.message.edit_text(f"✅ Местоположение сохранено: {city.title}")
    await callback.answer()


async def _save_location_and_refresh(
    *,
    session: AsyncSession,
    group: Group,
    city: City,
    prayer_times_service: PrayerTimesService,
    horizon_days: int,
) -> None:
    group_repo = GroupRepository(session)
    schedule_repo = PrayerScheduleRepository(session)

    location_changed = group.city_slug != city.slug
    await group_repo.update_location(
        group.id,
        city=city.title,
        city_slug=city.slug,
        latitude=city.lat,
        longitude=city.lng,
        timezone_label=format_offset_label(city.utc_offset_minutes),
        utc_offset_minutes=city.utc_offset_minutes,
    )
    today = datetime.now(UTC).date()
    if location_changed:
        await schedule_repo.delete_future(group.id, today)

    try:
        await ensure_schedule_cached(
            group_id=group.id,
            latitude=city.lat,
            longitude=city.lng,
            schedule_repo=schedule_repo,
            prayer_times_service=prayer_times_service,
            today=today,
            horizon_days=horizon_days,
        )
    except (PrayerTimesAPIError, PrayerTimesParseError):
        logger.exception("Failed to fetch prayer schedule right after location set for group_id=%s", group.id)


def _city_to_dict(city: City) -> dict:
    return {
        "title": city.title,
        "slug": city.slug,
        "lat": city.lat,
        "lng": city.lng,
        "utc_offset_minutes": city.utc_offset_minutes,
    }


def _city_from_dict(raw: dict) -> City:
    return City(
        title=raw["title"],
        slug=raw["slug"],
        lat=raw["lat"],
        lng=raw["lng"],
        utc_offset_minutes=raw["utc_offset_minutes"],
    )
