from datetime import date, datetime, time, timedelta
from datetime import timezone as dt_timezone

import pytest

from app.services.scheduler import compute_notify_at, is_juma_due, is_stale, should_send


def test_compute_notify_at_utc6():
    # Asr at 17:20 local (UTC+6), notify 15 minutes before -> 17:05 local -> 11:05 UTC.
    notify_at = compute_notify_at(date(2026, 1, 5), time(17, 20), utc_offset_minutes=360, prepare_minutes=15)
    assert notify_at == datetime(2026, 1, 5, 11, 5, tzinfo=dt_timezone.utc)


def test_compute_notify_at_negative_offset():
    notify_at = compute_notify_at(date(2026, 1, 5), time(12, 0), utc_offset_minutes=-300, prepare_minutes=0)
    assert notify_at == datetime(2026, 1, 5, 17, 0, tzinfo=dt_timezone.utc)


def test_is_stale_just_under_threshold():
    now = datetime(2026, 1, 5, 11, 14, 59, tzinfo=dt_timezone.utc)
    notify_at = datetime(2026, 1, 5, 11, 5, tzinfo=dt_timezone.utc)
    assert is_stale(now, notify_at, timedelta(minutes=10)) is False


def test_is_stale_just_over_threshold():
    now = datetime(2026, 1, 5, 11, 15, 1, tzinfo=dt_timezone.utc)
    notify_at = datetime(2026, 1, 5, 11, 5, tzinfo=dt_timezone.utc)
    assert is_stale(now, notify_at, timedelta(minutes=10)) is True


@pytest.mark.parametrize(
    ("now_offset_minutes", "notification_sent", "expected"),
    [
        (-5, False, "skip_not_due"),
        (0, True, "skip_already_sent"),
        (2, False, "send"),
        (11, False, "skip_stale"),
    ],
)
def test_should_send_branches(now_offset_minutes, notification_sent, expected):
    notify_at = datetime(2026, 1, 5, 11, 5, tzinfo=dt_timezone.utc)
    now = notify_at + timedelta(minutes=now_offset_minutes)
    assert should_send(now, notify_at, notification_sent, timedelta(minutes=10)) == expected


def test_is_juma_due_within_grace():
    now_local = datetime(2026, 1, 9, 12, 32, tzinfo=dt_timezone.utc)  # Friday
    assert is_juma_due(now_local, time(12, 30), timedelta(minutes=10)) is True


def test_is_juma_due_before_time():
    now_local = datetime(2026, 1, 9, 12, 29, tzinfo=dt_timezone.utc)
    assert is_juma_due(now_local, time(12, 30), timedelta(minutes=10)) is False


def test_is_juma_due_after_grace():
    now_local = datetime(2026, 1, 9, 12, 41, tzinfo=dt_timezone.utc)
    assert is_juma_due(now_local, time(12, 30), timedelta(minutes=10)) is False
