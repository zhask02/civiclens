from datetime import datetime
from math import asin, cos, radians, sin, sqrt

from pydantic import BaseModel, Field


# Mean radius of Earth in metres.
# Using metres means the geographic signal can be compared directly
# with CivicLens's duplicate-detection distance thresholds.
EARTH_RADIUS_METERS = 6_371_000


class DuplicateStatus(str):
    """
    Possible relationships between two incident reports.

    These are intentionally represented as simple strings for now.
    We can promote them to a project enum once the duplicate contract
    is used by the API and database.
    """

    DUPLICATE = "duplicate"
    RELATED = "related"
    SEPARATE = "separate"


class DuplicateAssessment(BaseModel):
    """
    Explainable result produced by DuplicateService.

    The assessment contains both the final relationship and the
    underlying evidence so operators and later components can inspect
    how the decision was reached.
    """

    # Final interpretation of the relationship between two incidents.
    status: str

    # Combined duplicate score bounded to a 0–100 range.
    score: float = Field(
        ge=0,
        le=100,
    )

    # Geographic separation between the incidents.
    distance_meters: float = Field(
        ge=0,
    )

    # Time separation between the incidents.
    time_difference_hours: float = Field(
        ge=0,
    )

    # Individual signal scores make the final decision explainable.
    location_score: float = Field(
        ge=0,
        le=100,
    )

    time_score: float = Field(
        ge=0,
        le=100,
    )

    # Human-readable evidence explaining the assessment.
    reasons: list[str]


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

    # Convert geographic angles from degrees to radians because Python's
    # trigonometric functions operate on radians.
    lat1 = radians(latitude_1)
    lon1 = radians(longitude_1)
    lat2 = radians(latitude_2)
    lon2 = radians(longitude_2)

    # Calculate the coordinate differences.
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    # Apply the Haversine formula to determine angular separation.
    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(delta_lon / 2) ** 2
    )

    # Convert angular separation into radians.
    c = 2 * asin(sqrt(a))

    # Convert angular distance into metres.
    return EARTH_RADIUS_METERS * c


def time_difference_hours(
    timestamp_1: datetime,
    timestamp_2: datetime,
) -> float:
    """
    Calculate the absolute time difference between two timestamps.

    Returning an absolute value means incident ordering does not matter.
    """

    # Convert the timestamp difference into seconds and then hours.
    difference = abs(
        (timestamp_1 - timestamp_2).total_seconds()
    )

    return difference / 3600.0


class DuplicateService:
    """
    Combines geographic and temporal evidence to assess two incidents.

    This service does not access the database or storage layer.
    Candidate incidents will be supplied by the caller, keeping this
    scoring logic independently testable.
    """

    # Geographic evidence is stronger than temporal coincidence for
    # determining whether two pothole reports describe the same defect.
    LOCATION_WEIGHT = 0.60
    TIME_WEIGHT = 0.40

    def assess(
        self,
        latitude_1: float,
        longitude_1: float,
        created_at_1: datetime,
        latitude_2: float,
        longitude_2: float,
        created_at_2: datetime,
    ) -> DuplicateAssessment:
        """
        Assess the relationship between two incident reports.
        """

        # Calculate the two independent pieces of raw evidence first.
        distance_meters = haversine_distance_meters(
            latitude_1,
            longitude_1,
            latitude_2,
            longitude_2,
        )

        time_difference = time_difference_hours(
            created_at_1,
            created_at_2,
        )

        # Convert geographic distance into a 0–100 similarity score.
        location_score = self._location_score(
            distance_meters
        )

        # Convert time separation into a 0–100 similarity score.
        time_score = self._time_score(
            time_difference
        )

        # Combine the independently calculated signals.
        score = round(
            location_score * self.LOCATION_WEIGHT
            + time_score * self.TIME_WEIGHT,
            2,
        )

        # Convert the numerical score into an operational relationship.
        status = self._score_to_status(score)

        # Keep the decision explainable to operators and future API users.
        reasons = [
            f"Reports are {distance_meters:.1f} m apart",
            (
                f"Reports were submitted "
                f"{time_difference:.1f} hours apart"
            ),
        ]

        return DuplicateAssessment(
            status=status,
            score=score,
            distance_meters=round(distance_meters, 2),
            time_difference_hours=round(time_difference, 2),
            location_score=location_score,
            time_score=time_score,
            reasons=reasons,
        )

    @staticmethod
    def _location_score(
        distance_meters: float,
    ) -> float:
        """Convert geographic separation into a similarity score."""

        if distance_meters <= 20:
            return 100.0

        if distance_meters <= 50:
            return 70.0

        if distance_meters <= 100:
            return 30.0

        return 0.0

    @staticmethod
    def _time_score(
        time_difference_hours_value: float,
    ) -> float:
        """Convert temporal separation into a similarity score."""

        if time_difference_hours_value <= 1:
            return 100.0

        if time_difference_hours_value <= 6:
            return 75.0

        if time_difference_hours_value <= 24:
            return 50.0

        if time_difference_hours_value <= 72:
            return 20.0

        return 0.0

    @staticmethod
    def _score_to_status(
        score: float,
    ) -> str:
        """Map the combined score to the final relationship."""

        if score >= 80:
            return DuplicateStatus.DUPLICATE

        if score >= 50:
            return DuplicateStatus.RELATED

        return DuplicateStatus.SEPARATE