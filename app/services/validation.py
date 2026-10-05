import re
from datetime import time

_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def validate_minutes(raw: str) -> int:
    text = raw.strip()
    if not re.fullmatch(r"\d+", text):
        raise ValueError("Количество минут должно быть положительным целым числом, например: 15")
    value = int(text)
    if value <= 0:
        raise ValueError("Количество минут должно быть больше нуля")
    if value > 180:
        raise ValueError("Слишком большое значение — укажите не более 180 минут")
    return value


def validate_time_hhmm(raw: str) -> time:
    text = raw.strip()
    match = _TIME_RE.fullmatch(text)
    if not match:
        raise ValueError("Некорректный формат времени. Укажите время как ЧЧ:ММ, например: 12:30")
    hours, minutes = int(match.group(1)), int(match.group(2))
    return time(hour=hours, minute=minutes)
