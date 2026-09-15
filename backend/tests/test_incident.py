"""
Tests for CivicLens incident lifecycle rules.

The lifecycle is a business rule that controls which status transitions
are allowed. These tests make that rule explicit and protect it from
accidental changes as the application grows.
"""

import pytest

from app.enums.incident import IncidentStatus
from app.services.incident import can_transition_status


def test_submitted_can_transition_to_analyzed():
    """A newly submitted incident can enter the analysis stage."""

    assert can_transition_status(
        IncidentStatus.SUBMITTED,
        IncidentStatus.ANALYZED,
    )


def test_analyzed_can_transition_to_assigned():
    """An analyzed incident can be assigned for handling."""

    assert can_transition_status(
        IncidentStatus.ANALYZED,
        IncidentStatus.ASSIGNED,
    )


def test_assigned_can_transition_to_in_progress():
    """An assigned incident can enter active resolution."""

    assert can_transition_status(
        IncidentStatus.ASSIGNED,
        IncidentStatus.IN_PROGRESS,
    )


def test_in_progress_can_transition_to_resolved():
    """An incident being worked on can be marked resolved."""

    assert can_transition_status(
        IncidentStatus.IN_PROGRESS,
        IncidentStatus.RESOLVED,
    )


def test_submitted_cannot_skip_directly_to_resolved():
    """
    An incident must follow the defined workflow instead of skipping
    directly from submission to resolution.
    """

    assert not can_transition_status(
        IncidentStatus.SUBMITTED,
        IncidentStatus.RESOLVED,
    )


def test_analyzed_cannot_skip_to_resolved():
    """An analyzed incident cannot bypass assignment and active work."""

    assert not can_transition_status(
        IncidentStatus.ANALYZED,
        IncidentStatus.RESOLVED,
    )


def test_assigned_cannot_skip_to_resolved():
    """An assigned incident must pass through in-progress first."""

    assert not can_transition_status(
        IncidentStatus.ASSIGNED,
        IncidentStatus.RESOLVED,
    )


def test_resolved_cannot_transition_to_another_status():
    """
    Resolution is terminal in the current CivicLens lifecycle.

    Once an incident is resolved, the workflow does not allow it to
    move back to an earlier state.
    """

    assert not can_transition_status(
        IncidentStatus.RESOLVED,
        IncidentStatus.SUBMITTED,
    )


def test_incident_cannot_transition_to_same_status():
    """
    Repeating the current status is not considered a lifecycle
    transition.
    """

    for status in IncidentStatus:
        assert not can_transition_status(status, status)