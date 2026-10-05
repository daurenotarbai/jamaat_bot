from datetime import date, time

import pytest

from app.services.prayer_times import DailyPrayerTimes, PrayerTimesParseError, PrayerTimesService


def _day(d: str, fajr="04:52", zuhr="13:10", asr="17:02", maghrib="19:34", isha="21:05") -> dict:
    return {"date": d, "fajr": fajr, "zuhr": zuhr, "asr": asr, "maghrib": maghrib, "isha": isha}


def test_parse_prayer_times_list_shape():
    raw = [_day("2026-01-01"), _day("2026-01-02")]
    result = PrayerTimesService._parse_prayer_times_response(raw)
    assert result == [
        DailyPrayerTimes(date(2026, 1, 1), time(4, 52), time(13, 10), time(17, 2), time(19, 34), time(21, 5)),
        DailyPrayerTimes(date(2026, 1, 2), time(4, 52), time(13, 10), time(17, 2), time(19, 34), time(21, 5)),
    ]


def test_parse_prayer_times_wrapped_in_results_key():
    raw = {"results": [_day("2026-01-01")]}
    result = PrayerTimesService._parse_prayer_times_response(raw)
    assert len(result) == 1
    assert result[0].date == date(2026, 1, 1)


def test_parse_prayer_times_real_dumk_shape():
    # Actual DUMK response: {"result": [...], "latitude", "longitude", "year", "city"},
    # each day keyed by "Date" (capitalized) and "dhuhr" instead of "zuhr".
    raw = {
        "result": [
            {
                "imsak": "06:09",
                "fajr": "05:59",
                "sunrise": "07:21",
                "dhuhr": "11:59",
                "asr": "14:48",
                "sunset": "16:27",
                "maghrib": "16:30",
                "isha": "17:53",
                "midnight": "23:56",
                "Date": "2026-01-01",
            }
        ],
        "latitude": "43.238293",
        "longitude": "76.945465",
        "year": 2026,
        "city": "Алматы қаласы",
    }
    result = PrayerTimesService._parse_prayer_times_response(raw)
    assert result == [
        DailyPrayerTimes(date(2026, 1, 1), time(5, 59), time(11, 59), time(14, 48), time(16, 30), time(17, 53)),
    ]


def test_parse_prayer_times_keyed_by_date_dict():
    raw = {"2026-01-01": _day("2026-01-01"), "2026-01-02": _day("2026-01-02")}
    result = PrayerTimesService._parse_prayer_times_response(raw)
    assert [d.date for d in result] == [date(2026, 1, 1), date(2026, 1, 2)]


def test_parse_prayer_times_dhuhr_alias_accepted():
    raw = [{"date": "2026-01-01", "fajr": "04:52", "dhuhr": "13:10", "asr": "17:02", "maghrib": "19:34", "isha": "21:05"}]
    result = PrayerTimesService._parse_prayer_times_response(raw)
    assert result[0].zuhr == time(13, 10)


def test_parse_prayer_times_missing_field_raises():
    raw = [{"date": "2026-01-01", "fajr": "04:52", "zuhr": "13:10", "maghrib": "19:34", "isha": "21:05"}]
    with pytest.raises(PrayerTimesParseError):
        PrayerTimesService._parse_prayer_times_response(raw)


def test_parse_prayer_times_unexpected_top_level_shape_raises():
    with pytest.raises(PrayerTimesParseError):
        PrayerTimesService._parse_prayer_times_response("not a list or dict")


def test_parse_prayer_times_empty_list_raises():
    with pytest.raises(PrayerTimesParseError):
        PrayerTimesService._parse_prayer_times_response([])


def test_parse_cities_response_valid():
    raw = [{"title": "Алматы", "slug": "almaty", "lat": "43.2389", "lng": "76.8897", "timezone": "6"}]
    cities = PrayerTimesService._parse_cities_response(raw)
    assert cities[0].title == "Алматы"
    assert cities[0].utc_offset_minutes == 360


def test_parse_cities_response_missing_field_raises():
    raw = [{"title": "Алматы", "slug": "almaty", "lat": "43.2389", "timezone": "6"}]
    with pytest.raises(PrayerTimesParseError):
        PrayerTimesService._parse_cities_response(raw)


def test_parse_cities_response_falls_back_to_id_when_no_slug():
    # The real DUMK API has no "slug" field -- only a numeric "id".
    raw = [
        {
            "id": 11256,
            "title": "Шоқпар (ст.)",
            "lng": "74.373333",
            "lat": "43.821389",
            "timezone": "5",
            "region": "Жамбыл облысы",
            "district": "Шу ауданы",
            "distance": None,
        }
    ]
    cities = PrayerTimesService._parse_cities_response(raw)
    assert cities[0].slug == "11256"
    assert cities[0].title == "Шоқпар (ст.)"


def test_parse_cities_response_empty_raises():
    with pytest.raises(PrayerTimesParseError):
        PrayerTimesService._parse_cities_response([])


def test_parse_cities_response_not_a_list_raises():
    with pytest.raises(PrayerTimesParseError):
        PrayerTimesService._parse_cities_response({"not": "a list"})
