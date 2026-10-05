import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

import httpx

from app.database.models.prayer_schedule import PRAYER_NAMES
from app.database.repositories.prayer_schedule_repository import PrayerScheduleRepository
from app.services.timezone import parse_utc_offset

logger = logging.getLogger(__name__)

_API_PRAYER_NAME_MAP = {
    "fajr": "fajr",
    "zuhr": "zuhr",
    "dhuhr": "zuhr",
    "asr": "asr",
    "maghrib": "maghrib",
    "isha": "isha",
}


@dataclass(frozen=True)
class City:
    title: str
    slug: str
    lat: float
    lng: float
    utc_offset_minutes: int


@dataclass(frozen=True)
class DailyPrayerTimes:
    date: date
    fajr: time
    zuhr: time
    asr: time
    maghrib: time
    isha: time

    def as_rows(self) -> list[tuple[date, str, time]]:
        return [
            (self.date, "fajr", self.fajr),
            (self.date, "zuhr", self.zuhr),
            (self.date, "asr", self.asr),
            (self.date, "maghrib", self.maghrib),
            (self.date, "isha", self.isha),
        ]


class PrayerTimesAPIError(Exception):
    """Raised when the DUMK API cannot be reached or returns a non-2xx response."""


class PrayerTimesParseError(Exception):
    """Raised when the DUMK API response has an unexpected shape."""


def _parse_time(raw: object, field: str) -> time:
    if isinstance(raw, str):
        text = raw.strip()
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(text, fmt).time()
            except ValueError:
                continue
    raise PrayerTimesParseError(f"Could not parse time for field {field!r}: {raw!r}")


def _parse_day_entry(raw: dict, fallback_date: date | None = None) -> DailyPrayerTimes:
    if not isinstance(raw, dict):
        raise PrayerTimesParseError(f"Expected a day object, got {type(raw).__name__}")

    day_date = fallback_date
    for date_key in ("date", "day", "Date"):
        if date_key in raw:
            raw_date = raw[date_key]
            try:
                day_date = (
                    raw_date
                    if isinstance(raw_date, date)
                    else datetime.strptime(str(raw_date)[:10], "%Y-%m-%d").date()
                )
            except ValueError as exc:
                raise PrayerTimesParseError(f"Could not parse date {raw_date!r}") from exc
            break
    if day_date is None:
        raise PrayerTimesParseError("Day entry is missing a date and no fallback date was supplied")

    times: dict[str, time] = {}
    for api_key, canonical in _API_PRAYER_NAME_MAP.items():
        if api_key in raw:
            times[canonical] = _parse_time(raw[api_key], api_key)

    missing = [name for name in PRAYER_NAMES if name not in times]
    if missing:
        raise PrayerTimesParseError(f"Day entry for {day_date} is missing prayer times: {missing}")

    return DailyPrayerTimes(
        date=day_date,
        fajr=times["fajr"],
        zuhr=times["zuhr"],
        asr=times["asr"],
        maghrib=times["maghrib"],
        isha=times["isha"],
    )


class PrayerTimesService:
    def __init__(self, http_client: httpx.AsyncClient, base_url: str) -> None:
        self._http = http_client
        self._base_url = base_url.rstrip("/")
        self._cities_cache: list[City] | None = None

    async def get_cities(self) -> list[City]:
        """Fetches the full DUMK city list, transparently following DRF-style pagination
        (`{"count", "next", "results"}`). Cached in-process for the lifetime of the
        service instance -- the city list barely changes and paginates over ~60 requests,
        so refetching it on every /set_location call would be wasteful and slow."""
        if self._cities_cache is not None:
            return self._cities_cache

        raw_entries: list[object] = []
        next_url: str | None = f"{self._base_url}/cities/"
        while next_url:
            try:
                response = await self._http.get(next_url)
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPError as exc:
                raise PrayerTimesAPIError(f"Failed to fetch city list from {next_url}") from exc
            except ValueError as exc:
                raise PrayerTimesParseError(f"Non-JSON response from {next_url}") from exc

            if isinstance(payload, list):
                raw_entries.extend(payload)
                next_url = None
            elif isinstance(payload, dict) and "results" in payload:
                raw_entries.extend(payload.get("results") or [])
                next_url = payload.get("next")
            else:
                raise PrayerTimesParseError(f"Unrecognized city list response shape at {next_url}")

        cities = self._parse_cities_response(raw_entries)
        self._cities_cache = cities
        return cities

    async def get_prayer_times(self, year: int, latitude: float, longitude: float) -> list[DailyPrayerTimes]:
        url = f"{self._base_url}/prayer-times/{year}/{latitude}/{longitude}"
        try:
            response = await self._http.get(url)
            response.raise_for_status()
            raw = response.json()
        except httpx.HTTPError as exc:
            raise PrayerTimesAPIError(f"Failed to fetch prayer times from {url}") from exc
        except ValueError as exc:
            raise PrayerTimesParseError(f"Non-JSON response from {url}") from exc
        return self._parse_prayer_times_response(raw)

    @staticmethod
    def _parse_cities_response(raw: object) -> list[City]:
        if not isinstance(raw, list):
            raise PrayerTimesParseError(f"Expected a list of cities, got {type(raw).__name__}")

        cities: list[City] = []
        for entry in raw:
            if not isinstance(entry, dict):
                raise PrayerTimesParseError(f"Expected a city object, got {type(entry).__name__}")
            try:
                # The live DUMK API has no "slug" field (despite the documented example) --
                # it identifies cities by a numeric "id" instead. Prefer "slug" when present
                # for forward-compatibility, fall back to "id" otherwise.
                raw_slug = entry.get("slug")
                if raw_slug is None:
                    raw_slug = entry["id"]
                cities.append(
                    City(
                        title=str(entry["title"]),
                        slug=str(raw_slug),
                        lat=float(entry["lat"]),
                        lng=float(entry["lng"]),
                        utc_offset_minutes=parse_utc_offset(entry["timezone"]),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise PrayerTimesParseError(f"Malformed city entry: {entry!r}") from exc
        if not cities:
            raise PrayerTimesParseError("City list response was empty")
        return cities

    @staticmethod
    def _parse_prayer_times_response(raw: object) -> list[DailyPrayerTimes]:
        if isinstance(raw, dict):
            entries = raw.get("result") or raw.get("results") or raw.get("data") or raw.get("prayer_times")
            if entries is None:
                # Some DUMK endpoints key the response by date string, e.g. {"2026-01-01": {...}}.
                entries = []
                for key, value in raw.items():
                    try:
                        day_date = datetime.strptime(key[:10], "%Y-%m-%d").date()
                    except ValueError:
                        continue
                    entries.append(_parse_day_entry(value, fallback_date=day_date))
                if not entries:
                    raise PrayerTimesParseError(f"Unrecognized prayer-times response shape: {list(raw.keys())!r}")
                return sorted(entries, key=lambda e: e.date)
        elif isinstance(raw, list):
            entries = raw
        else:
            raise PrayerTimesParseError(f"Expected a list or dict, got {type(raw).__name__}")

        if not isinstance(entries, list):
            raise PrayerTimesParseError("Prayer-times response did not contain a list of days")

        parsed = [_parse_day_entry(entry) for entry in entries]
        if not parsed:
            raise PrayerTimesParseError("Prayer-times response contained no days")
        return sorted(parsed, key=lambda e: e.date)


async def ensure_schedule_cached(
    *,
    group_id: int,
    latitude: float,
    longitude: float,
    schedule_repo: PrayerScheduleRepository,
    prayer_times_service: PrayerTimesService,
    today: date,
    horizon_days: int,
) -> None:
    """Makes sure prayer_schedules covers [today, today + horizon_days] for this group.

    On API failure, logs and leaves whatever is already cached in place (per spec: fall
    back to previously stored data when the DUMK API is temporarily unavailable).
    """
    needed_until = today + timedelta(days=horizon_days)
    _min_date, max_date = await schedule_repo.coverage_range(group_id)
    if max_date is not None and max_date >= needed_until:
        return

    years_needed = {today.year, needed_until.year}
    all_days: list[DailyPrayerTimes] = []
    for year in sorted(years_needed):
        try:
            all_days.extend(await prayer_times_service.get_prayer_times(year, latitude, longitude))
        except (PrayerTimesAPIError, PrayerTimesParseError):
            logger.exception("Failed to refresh prayer schedule for group_id=%s year=%s", group_id, year)

    relevant = [d for d in all_days if today <= d.date <= needed_until]
    if not relevant:
        return

    rows: list[tuple[date, str, time]] = []
    for day in relevant:
        rows.extend(day.as_rows())
    await schedule_repo.upsert_batch(group_id, rows)
