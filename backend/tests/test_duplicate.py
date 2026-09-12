from datetime import datetime, timedelta, timezone

import pytest

from app.services.duplicate import (
    haversine_distance_meters,
    time_difference_hours,
)


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


def test_same_timestamp_has_zero_time_difference():
    """Identical timestamps should produce a zero-hour difference."""

    timestamp = datetime(
        2026,
        9,
        12,
        10,
        0,
        tzinfo=timezone.utc,
    )

    difference = time_difference_hours(
        timestamp,
        timestamp,
    )

    assert difference == pytest.approx(0.0)


def test_time_difference_is_measured_in_hours():
    """A six-hour separation should be returned as exactly six hours."""

    first = datetime(
        2026,
        9,
        12,
        10,
        0,
        tzinfo=timezone.utc,
    )

    second = first + timedelta(hours=6)

    difference = time_difference_hours(
        first,
        second,
    )

    assert difference == pytest.approx(6.0)


def test_time_difference_is_symmetric():
    """Swapping timestamps must not change the time difference."""

    first = datetime(
        2026,
        9,
        12,
        10,
        0,
        tzinfo=timezone.utc,
    )

    second = first + timedelta(hours=24)

    forward = time_difference_hours(first, second)
    reverse = time_difference_hours(second, first)

    assert forward == pytest.approx(reverse)


def test_time_difference_handles_minutes():
    """Sub-hour differences should retain fractional-hour precision."""

    first = datetime(
        2026,
        9,
        12,
        10,
        0,
        tzinfo=timezone.utc,
    )

    second = first + timedelta(minutes=30)

    difference = time_difference_hours(
        first,
        second,
    )

    assert difference == pytest.approx(0.5)