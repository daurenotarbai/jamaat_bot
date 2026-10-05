from datetime import timedelta

import pytest

from app.services.timezone import TimezoneParseError, format_offset_label, offset_to_tzinfo, parse_utc_offset


@pytest.mark.parametrize("raw", ["6", "+6", 6, "UTC+6", "UTC 6"])
def test_parse_utc_offset_variants(raw):
    assert parse_utc_offset(raw) == 360


def test_parse_utc_offset_negative():
    assert parse_utc_offset("-5") == -300


def test_parse_utc_offset_invalid_raises():
    with pytest.raises(TimezoneParseError):
        parse_utc_offset("not-a-timezone")


def test_offset_to_tzinfo_matches_offset():
    tzinfo = offset_to_tzinfo(360)
    assert tzinfo.utcoffset(None) == timedelta(hours=6)


def test_format_offset_label_positive():
    assert format_offset_label(360) == "UTC+6"


def test_format_offset_label_negative():
    assert format_offset_label(-300) == "UTC-5"


def test_format_offset_label_with_fractional_hours():
    assert format_offset_label(345) == "UTC+5:45"
