import pytest

from app.services.duplicate import haversine_distance_meters


def test_same_coordinates_have_zero_distance():
    """Identical GPS points should have no geographic separation."""

    distance = haversine_distance_meters(
        12.8406,
        80.1534,
        12.8406,
        80.1534,
    )

    assert distance == pytest.approx(0.0)


def test_distance_is_measured_in_meters():
    """
    Two nearby coordinates should produce a realistic metric distance,
    rather than a tiny value expressed in degrees.
    """

    distance = haversine_distance_meters(
        12.8406,
        80.1534,
        12.8406,
        80.1536,
    )

    # This longitude difference at Chennai's latitude is roughly 22 m.
    assert distance == pytest.approx(21.7, abs=1.0)


def test_distance_is_symmetric():
    """Swapping the two GPS points must not change their distance."""

    distance_forward = haversine_distance_meters(
        12.8406,
        80.1534,
        12.8410,
        80.1534,
    )

    distance_reverse = haversine_distance_meters(
        12.8410,
        80.1534,
        12.8406,
        80.1534,
    )

    assert distance_forward == pytest.approx(distance_reverse)


def test_known_global_distance():
    """
    Check the implementation against a well-known approximate
    Earth-surface distance between two distant coordinates.
    """

    distance = haversine_distance_meters(
        0.0,
        0.0,
        1.0,
        0.0,
    )

    # One degree of latitude is approximately 111.2 km.
    assert distance == pytest.approx(111_195, rel=0.001)