from datetime import time

import pytest

from app.services.validation import validate_minutes, validate_time_hhmm


def test_validate_minutes_valid():
    assert validate_minutes("15") == 15


@pytest.mark.parametrize("raw", ["0", "-1", "abc", "", "15.5", "999"])
def test_validate_minutes_invalid(raw):
    with pytest.raises(ValueError):
        validate_minutes(raw)


def test_validate_time_hhmm_valid():
    assert validate_time_hhmm("12:30") == time(12, 30)


@pytest.mark.parametrize("raw", ["25:00", "12:60", "12.30", "noon", "", "1230"])
def test_validate_time_hhmm_invalid(raw):
    with pytest.raises(ValueError):
        validate_time_hhmm(raw)
