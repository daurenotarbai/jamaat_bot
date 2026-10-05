import pytest

from app.services.prayer_times import PrayerTimesAPIError, PrayerTimesService


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakePaginatedClient:
    """Mimics DRF-style pagination: page 1 has `next`, page 2 doesn't."""

    def __init__(self):
        self.calls: list[str] = []

    async def get(self, url: str) -> _FakeResponse:
        self.calls.append(url)
        if url.endswith("/cities/"):
            return _FakeResponse(
                {
                    "count": 2,
                    "next": "https://api.example.test/cities/?page=2",
                    "results": [{"title": "Алматы", "slug": "almaty", "lat": "43.2", "lng": "76.9", "timezone": "6"}],
                }
            )
        return _FakeResponse(
            {
                "count": 2,
                "next": None,
                "results": [{"title": "Астана", "slug": "astana", "lat": "51.1", "lng": "71.4", "timezone": "5"}],
            }
        )


@pytest.mark.asyncio
async def test_get_cities_follows_pagination_and_merges_results():
    client = _FakePaginatedClient()
    service = PrayerTimesService(client, "https://api.example.test")

    cities = await service.get_cities()

    assert [c.slug for c in cities] == ["almaty", "astana"]
    assert len(client.calls) == 2


@pytest.mark.asyncio
async def test_get_cities_caches_after_first_call():
    client = _FakePaginatedClient()
    service = PrayerTimesService(client, "https://api.example.test")

    await service.get_cities()
    await service.get_cities()

    assert len(client.calls) == 2  # not re-fetched on the second call


@pytest.mark.asyncio
async def test_get_cities_wraps_transport_errors():
    import httpx

    class _HttpErrorClient:
        async def get(self, url: str):
            raise httpx.ConnectError("unreachable")

    service = PrayerTimesService(_HttpErrorClient(), "https://api.example.test")

    with pytest.raises(PrayerTimesAPIError):
        await service.get_cities()
