import re
from datetime import timedelta, timezone

_OFFSET_RE = re.compile(r"^(?:UTC)?\s*([+-]?\d+(?:\.\d+)?)$", re.IGNORECASE)


class TimezoneParseError(ValueError):
    """Raised when a UTC-offset value from the DUMK API cannot be understood."""


def parse_utc_offset(raw: int | float | str) -> int:
    """Parses a DUMK-style UTC offset (e.g. 6, "6", "+6", "UTC+6", 5.75) into minutes."""
    if isinstance(raw, (int, float)):
        hours = float(raw)
    else:
        match = _OFFSET_RE.match(str(raw).strip())
        if not match:
            raise TimezoneParseError(f"Unrecognized UTC offset: {raw!r}")
        hours = float(match.group(1))

    minutes = round(hours * 60)
    if not -720 <= minutes <= 840:
        raise TimezoneParseError(f"UTC offset out of range: {raw!r}")
    return minutes


def offset_to_tzinfo(minutes: int) -> timezone:
    return timezone(timedelta(minutes=minutes))


def format_offset_label(minutes: int) -> str:
    sign = "+" if minutes >= 0 else "-"
    total = abs(minutes)
    hours, mins = divmod(total, 60)
    if mins:
        return f"UTC{sign}{hours}:{mins:02d}"
    return f"UTC{sign}{hours}"
