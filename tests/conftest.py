import pytest

from app.services.prayer_times import City


@pytest.fixture
def sample_cities() -> list[City]:
    return [
        City(title="Алматы", slug="almaty", lat=43.2389, lng=76.8897, utc_offset_minutes=360),
        City(title="Астана", slug="astana", lat=51.1694, lng=71.4491, utc_offset_minutes=300),
        City(title="Шымкент", slug="shymkent", lat=42.3417, lng=69.5901, utc_offset_minutes=300),
    ]
