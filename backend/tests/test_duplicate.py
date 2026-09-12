from datetime import datetime, timedelta, timezone

import pytest

from app.services.duplicate import (
    haversine_distance_meters,
    time_difference_hours,
    DuplicateService,
    DuplicateStatus,
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

def test_close_recent_incidents_are_duplicates():
    """
    Very close reports submitted shortly apart should receive strong
    duplicate evidence from both geographic and temporal signals.
    """

    service = DuplicateService()

    first = datetime(
        2026,
        9,
        12,
        10,
        0,
        tzinfo=timezone.utc,
    )

    second = first + timedelta(minutes=30)

    assessment = service.assess(
        12.8406,
        80.1534,
        first,
        12.84065,
        80.15345,
        second,
    )

    assert assessment.status == DuplicateStatus.DUPLICATE
    assert assessment.score == pytest.approx(100.0)
    assert assessment.location_score == 100.0
    assert assessment.time_score == 100.0


def test_moderately_close_incidents_are_related():
    """
    Reports within roughly 50 m and several hours apart should retain
    meaningful relationship evidence without being treated as certain
    duplicates.
    """

    service = DuplicateService()

    first = datetime(
        2026,
        9,
        12,
        10,
        0,
        tzinfo=timezone.utc,
    )

    second = first + timedelta(hours=6)

    assessment = service.assess(
        12.8406,
        80.1534,
        first,
        12.8409,
        80.1534,
        second,
    )

    assert assessment.status == DuplicateStatus.RELATED
    assert assessment.score == pytest.approx(72.0)


def test_distant_incidents_are_separate():
    """
    Reports more than 100 m apart should receive no geographic
    similarity even when they were submitted at the same time.
    """

    service = DuplicateService()

    timestamp = datetime(
        2026,
        9,
        12,
        10,
        0,
        tzinfo=timezone.utc,
    )

    assessment = service.assess(
        12.8406,
        80.1534,
        timestamp,
        12.8420,
        80.1534,
        timestamp,
    )

    assert assessment.status == DuplicateStatus.SEPARATE
    assert assessment.location_score == 0.0
    assert assessment.time_score == 100.0


def test_old_reports_do_not_become_duplicates_from_location_alone():
    """
    A geographically close report from several days earlier should
    receive weaker temporal evidence rather than being treated as an
    automatic duplicate.
    """

    service = DuplicateService()

    first = datetime(
        2026,
        9,
        5,
        10,
        0,
        tzinfo=timezone.utc,
    )

    second = first + timedelta(days=4)

    assessment = service.assess(
        12.8406,
        80.1534,
        first,
        12.84065,
        80.15345,
        second,
    )

    assert assessment.status == DuplicateStatus.RELATED
    assert assessment.location_score == 100.0
    assert assessment.time_score == 0.0
    assert assessment.score == pytest.approx(60.0)


def test_assessment_contains_explanations():
    """Every assessment should expose human-readable supporting evidence."""

    service = DuplicateService()

    timestamp = datetime(
        2026,
        9,
        12,
        10,
        0,
        tzinfo=timezone.utc,
    )

    assessment = service.assess(
        12.8406,
        80.1534,
        timestamp,
        12.8406,
        80.1534,
        timestamp,
    )

    assert len(assessment.reasons) == 2
    assert "m apart" in assessment.reasons[0]
    assert "hours apart" in assessment.reasons[1]