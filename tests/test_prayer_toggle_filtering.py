from datetime import time

from app.bot.formatting import format_settings_text
from app.database.models.group import Group
from app.database.models.group_prayer_setting import DEFAULT_PRAYER_TOGGLES
from app.database.models.prayer_schedule import PRAYER_NAMES


def test_default_prayer_toggles_match_spec():
    assert DEFAULT_PRAYER_TOGGLES == {
        "fajr": False,
        "zuhr": True,
        "asr": True,
        "maghrib": True,
        "isha": False,
    }


def test_prayer_names_canonical_order():
    assert PRAYER_NAMES == ("fajr", "zuhr", "asr", "maghrib", "isha")


def _make_group(**overrides) -> Group:
    defaults = dict(
        telegram_chat_id=1,
        title="Test group",
        city="Алматы",
        city_slug="almaty",
        latitude=43.2389,
        longitude=76.8897,
        utc_offset_minutes=360,
        prepare_pray_minutes=15,
        juma_notification_time=time(12, 30),
    )
    defaults.update(overrides)
    return Group(**defaults)


def test_format_settings_text_without_location_prompts_set_location():
    group = Group(telegram_chat_id=1, title="Test group")
    text = format_settings_text(group, {})
    assert "не настроено" in text
    assert "/set_location" in text


def test_format_settings_text_lists_prayers_in_canonical_order_with_marks():
    group = _make_group()
    text = format_settings_text(group, DEFAULT_PRAYER_TOGGLES)
    lines = [line for line in text.splitlines() if line.startswith(("✅", "❌"))]
    assert lines == [
        "❌ Фаджр",
        "✅ Зухр",
        "✅ Аср",
        "✅ Магриб",
        "❌ Иша",
    ]


def test_format_settings_text_includes_prepare_minutes_and_juma_time():
    group = _make_group(prepare_pray_minutes=20, juma_notification_time=time(13, 0))
    text = format_settings_text(group, DEFAULT_PRAYER_TOGGLES)
    assert "За: 20 минут" in text
    assert "Джума: 13:00" in text
