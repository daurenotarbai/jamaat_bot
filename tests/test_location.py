import pytest

from app.services.location import find_nearest_city, haversine_km, is_within_threshold


def test_haversine_known_distance():
    # Almaty -> Astana, real-world distance is ~970 km.
    distance = haversine_km(43.2389, 76.8897, 51.1694, 71.4491)
    assert 950 <= distance <= 990


def test_haversine_zero_for_identical_points():
    assert haversine_km(43.2389, 76.8897, 43.2389, 76.8897) == pytest.approx(0.0, abs=1e-6)


def test_find_nearest_city_picks_closest(sample_cities):
    # A point right next to Almaty.
    city, distance = find_nearest_city(sample_cities, 43.25, 76.90)
    assert city.slug == "almaty"
    assert distance < 5


def test_find_nearest_city_empty_list_raises():
    with pytest.raises(ValueError):
        find_nearest_city([], 43.0, 76.0)


@pytest.mark.parametrize(
    ("distance_km", "expected"),
    [
        (0.0, True),
        (79.9, True),
        (80.0, True),
        (80.1, False),
        (150.0, False),
    ],
)
def test_is_within_threshold_boundary(distance_km, expected):
    assert is_within_threshold(distance_km, threshold_km=80.0) is expected
