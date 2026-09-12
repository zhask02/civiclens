from datetime import datetime
from math import asin, cos, radians, sin, sqrt


# Mean radius of Earth in metres.
# Using metres here means callers get a directly useful geographic distance.
EARTH_RADIUS_METERS = 6_371_000


def haversine_distance_meters(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    """
    Calculate the great-circle distance between two GPS coordinates.

    Haversine is appropriate for CivicLens because latitude and longitude
    are angular coordinates rather than flat x/y metre coordinates.

    Returns:
        Distance between the two points in metres.
    """

    # Convert all geographic angles from degrees to radians because
    # Python's trigonometric functions operate on radians.
    lat1 = radians(latitude_1)
    lon1 = radians(longitude_1)
    lat2 = radians(latitude_2)
    lon2 = radians(longitude_2)

    # Calculate the differences between the two coordinates.
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    # Haversine formula:
    # a represents the angular separation between the two points.
    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(delta_lon / 2) ** 2
    )

    # Convert the angular separation into radians.
    c = 2 * asin(sqrt(a))

    # Multiply by Earth's radius to obtain the distance in metres.
    return EARTH_RADIUS_METERS * c


def time_difference_hours(
    timestamp_1: datetime,
    timestamp_2: datetime,
) -> float:
    """
    Calculate the absolute time difference between two incident timestamps.

    Returning the absolute difference means the function does not care
    which incident was submitted first. Duplicate detection can therefore
    compare incidents in either order.

    Returns:
        Time difference in hours.
    """

    # timedelta.total_seconds() gives us an exact duration, which we
    # convert to hours for the duplicate-detection rules.
    difference = abs(
        (timestamp_1 - timestamp_2).total_seconds()
    )

    return difference / 3600.0