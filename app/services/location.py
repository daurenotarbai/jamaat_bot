from math import atan2, cos, radians, sin, sqrt

from app.services.prayer_times import City

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(p1) * cos(p2) * sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * atan2(sqrt(a), sqrt(1 - a))


def find_nearest_city(cities: list[City], lat: float, lng: float) -> tuple[City, float]:
    if not cities:
        raise ValueError("City list is empty")
    return min(((c, haversine_km(lat, lng, c.lat, c.lng)) for c in cities), key=lambda pair: pair[1])


def is_within_threshold(distance_km: float, threshold_km: float) -> bool:
    return distance_km <= threshold_km
