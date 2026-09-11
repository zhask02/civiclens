import pytest

from app.enums.incident import IncidentSeverity
from app.schemas.location import CivicContext
from app.services.priority import PriorityEngine


@pytest.fixture
def engine() -> PriorityEngine:
    """Create a fresh Priority Engine for each test."""
    return PriorityEngine()


def test_critical_campus_high_confidence_is_critical(engine):
    # Critical severity starts at 100 and campus uses the baseline 1.0
    # multiplier, so highly confident evidence should remain critical.
    result = engine.calculate(
        severity=IncidentSeverity.CRITICAL,
        civic_context=CivicContext.CAMPUS,
        confidence=0.90,
    )

    assert result.score == 100.0
    assert result.level == IncidentSeverity.CRITICAL
    assert result.requires_review is False


def test_low_parking_high_confidence_is_low(engine):
    # A low-severity pothole in a parking area should be dampened
    # by the lower-risk parking multiplier.
    result = engine.calculate(
        severity=IncidentSeverity.LOW,
        civic_context=CivicContext.PARKING,
        confidence=0.90,
    )

    assert result.score == 22.5
    assert result.level == IncidentSeverity.LOW
    assert result.requires_review is False


def test_medium_campus_moderate_confidence_is_dampened(engine):
    # Confidence between 0.50 and 0.69 applies the agreed 0.85
    # reliability factor without requiring human review.
    result = engine.calculate(
        severity=IncidentSeverity.MEDIUM,
        civic_context=CivicContext.CAMPUS,
        confidence=0.60,
    )

    assert result.score == 42.5
    assert result.level == IncidentSeverity.MEDIUM
    assert result.requires_review is False


def test_low_confidence_requires_review(engine):
    # Low confidence should explicitly surface uncertainty rather than
    # pretending that the automated result is fully trustworthy.
    result = engine.calculate(
        severity=IncidentSeverity.HIGH,
        civic_context=CivicContext.CAMPUS,
        confidence=0.40,
    )

    assert result.score == 63.75
    assert result.level == IncidentSeverity.MEDIUM
    assert result.requires_review is True


def test_unknown_location_dampens_priority(engine):
    # Unknown context should reduce priority rather than assuming
    # that an unclassified location has normal public-road risk.
    result = engine.calculate(
        severity=IncidentSeverity.HIGH,
        civic_context=CivicContext.UNKNOWN,
        confidence=0.90,
    )

    assert result.score == 60.0
    assert result.level == IncidentSeverity.MEDIUM


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_invalid_confidence_is_rejected(engine, confidence):
    # Confidence outside the valid 0.0–1.0 range indicates a programming
    # or upstream-data error and should not silently produce a score.
    with pytest.raises(ValueError, match="Confidence must be between"):
        engine.calculate(
            severity=IncidentSeverity.MEDIUM,
            civic_context=CivicContext.CAMPUS,
            confidence=confidence,
        )