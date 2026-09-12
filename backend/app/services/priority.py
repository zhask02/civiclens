from app.enums.incident import IncidentSeverity, PriorityLevel
from app.schemas.location import CivicContext
from app.schemas.priority import PriorityResult


class PriorityEngine:
    """
    Calculates incident priority using deterministic business rules.

    The engine deliberately has no database, API, Redis, or ML dependency.
    This keeps the prioritization logic easy to audit and unit test.
    """

    # Severity is the primary risk signal.
    SEVERITY_SCORES = {
        IncidentSeverity.LOW: 25.0,
        IncidentSeverity.MEDIUM: 50.0,
        IncidentSeverity.HIGH: 75.0,
        IncidentSeverity.CRITICAL: 100.0,
    }

    # Location modifies the base physical risk.
    #
    # Only contexts currently supported by CivicLens v1 are included here.
    # We can add public-road/highway/residential contexts later when the
    # location layer provides those distinctions reliably.
    LOCATION_MULTIPLIERS = {
        CivicContext.UNKNOWN: 0.8,
        CivicContext.PARKING: 0.9,
        CivicContext.CAMPUS: 1.0,
    }

    def calculate(
        self,
        severity: IncidentSeverity,
        civic_context: CivicContext,
        confidence: float,
    ) -> PriorityResult:
        """
        Calculate an incident's priority from severity, location, and confidence.

        Confidence does not represent physical danger. It only determines
        how strongly the system should trust the visual analysis.
        """

        # Reject impossible confidence values early so the engine's
        # calculations always operate on a valid probability-like value.
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")

        # Look up the primary danger score from the detected severity.
        base_score = self.SEVERITY_SCORES[severity]

        # Apply the contextual risk modifier supplied by the location layer.
        location_multiplier = self.LOCATION_MULTIPLIERS[civic_context]

        # Confidence below 0.50 is too uncertain for an ordinary automated
        # priority decision, so flag it for human review.
        requires_review = confidence < 0.50

        # Apply the agreed soft confidence penalty to moderately uncertain
        # detections. Very confident detections retain their full score.
        if confidence >= 0.70:
            confidence_factor = 1.0
        elif confidence >= 0.50:
            confidence_factor = 0.85
        else:
            confidence_factor = 0.85

        # Combine the primary danger signal with location and evidence
        # reliability, while preventing the score from exceeding 100.
        score = min(
            100.0,
            base_score * location_multiplier * confidence_factor,
        )

        # Convert the numerical score into an operational priority level.
        level = self._score_to_level(score)

        return PriorityResult(
            score=score,
            level=level,
            requires_review=requires_review,
        )

    # Convert the numerical priority score into the separate operational
    # priority vocabulary used by CivicLens.
    @staticmethod
    def _score_to_level(score: float) -> PriorityLevel:
        """
        Convert a bounded numerical score into an operational priority level.
        """

        # Very high scores represent incidents that should be handled urgently.
        if score >= 85:
            return PriorityLevel.CRITICAL

        # High scores represent significant operational urgency.
        if score >= 70:
            return PriorityLevel.HIGH

        # Moderate scores require normal prioritization.
        if score >= 40:
            return PriorityLevel.MEDIUM

        # Everything below 40 is ordinary/low operational priority.
        return PriorityLevel.LOW