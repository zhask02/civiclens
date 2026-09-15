"""
Duplicate detection utilities for CivicLens.

This module contains the deterministic comparison logic used to decide
whether two pothole incidents are likely duplicates, related reports,
or separate incidents.

The service combines three independent signals:

    1. Geographic similarity
    2. Temporal similarity
    3. Visual similarity

Visual similarity is based on cosine similarity between normalized
image embeddings produced by VisualEmbeddingService.
"""

from datetime import datetime
from enum import Enum
import math

import numpy as np
from pydantic import BaseModel, Field


# Mean radius of Earth in meters.
#
# Using meters here keeps the location thresholds in the same units
# that CivicLens uses for duplicate detection.
EARTH_RADIUS_METERS = 6_371_000


class DuplicateStatus(str, Enum):
    """
    Final classification produced by DuplicateService.

    DUPLICATE means the evidence strongly suggests the reports describe
    the same physical pothole.

    RELATED means the reports may concern the same area or issue but the
    evidence is not strong enough to merge them automatically.

    SEPARATE means the available evidence does not indicate a duplicate.
    """

    DUPLICATE = "duplicate"
    RELATED = "related"
    SEPARATE = "separate"


class DuplicateAssessment(BaseModel):
    """
    Structured result of comparing two incident reports.

    Keeping individual component scores makes the decision explainable
    instead of returning only a final DUPLICATE/RELATED/SEPARATE label.
    """

    status: DuplicateStatus
    score: float = Field(ge=0.0, le=100.0)

    distance_meters: float
    time_difference_hours: float

    location_score: float = Field(ge=0.0, le=100.0)
    time_score: float = Field(ge=0.0, le=100.0)
    visual_score: float = Field(ge=0.0, le=100.0)

    reasons: list[str]


def haversine_distance_meters(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float,
) -> float:
    """
    Calculate the great-circle distance between two GPS coordinates.

    Haversine is appropriate for CivicLens because latitude and
    longitude are angular coordinates rather than flat Cartesian
    x/y coordinates.
    """

    latitude_1_rad = math.radians(latitude_1)
    latitude_2_rad = math.radians(latitude_2)

    delta_latitude = math.radians(latitude_2 - latitude_1)
    delta_longitude = math.radians(longitude_2 - longitude_1)

    haversine = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(latitude_1_rad)
        * math.cos(latitude_2_rad)
        * math.sin(delta_longitude / 2) ** 2
    )

    angular_distance = 2 * math.atan2(
        math.sqrt(haversine),
        math.sqrt(1 - haversine),
    )

    return EARTH_RADIUS_METERS * angular_distance


def time_difference_hours(
    timestamp_1: datetime,
    timestamp_2: datetime,
) -> float:
    """
    Return the absolute difference between two timestamps in hours.

    Absolute difference makes the function independent of which
    incident is passed first.
    """

    difference_seconds = abs(
        (timestamp_2 - timestamp_1).total_seconds()
    )

    return difference_seconds / 3600


def cosine_similarity(
    embedding_1: np.ndarray,
    embedding_2: np.ndarray,
) -> float:
    """
    Calculate cosine similarity between two visual embeddings.

    The VisualEmbeddingService already normalizes its output vectors,
    but this function still validates the vectors and normalizes them
    independently so that the mathematical helper remains safe to use
    on arbitrary NumPy arrays.

    Returns:
        A similarity value in the range [-1, 1].
    """

    # Convert the inputs explicitly to floating-point arrays so the
    # calculation behaves consistently regardless of input dtype.
    vector_1 = np.asarray(embedding_1, dtype=float)
    vector_2 = np.asarray(embedding_2, dtype=float)

    # Flatten the vectors because embeddings should represent a single
    # feature vector rather than a matrix or higher-dimensional tensor.
    vector_1 = vector_1.reshape(-1)
    vector_2 = vector_2.reshape(-1)

    # Comparing vectors with different dimensions is mathematically
    # undefined, so reject the inputs before calculating similarity.
    if vector_1.shape != vector_2.shape:
        raise ValueError(
            "Embedding vectors must have the same dimensions"
        )

    norm_1 = np.linalg.norm(vector_1)
    norm_2 = np.linalg.norm(vector_2)

    # Zero vectors cannot be normalized and therefore do not have a
    # meaningful cosine similarity.
    if norm_1 == 0 or norm_2 == 0:
        raise ValueError(
            "Embedding vectors must have non-zero magnitude"
        )

    # Normalize locally so this helper works correctly even if a caller
    # supplies embeddings that were not produced by our service.
    normalized_1 = vector_1 / norm_1
    normalized_2 = vector_2 / norm_2

    similarity = float(
        np.dot(normalized_1, normalized_2)
    )

    # Numerical floating-point operations can produce values such as
    # 1.0000000002, so clamp the result to cosine similarity's valid
    # mathematical range.
    return float(np.clip(similarity, -1.0, 1.0))


class DuplicateService:
    """
    Combine geographic, temporal, and visual evidence.

    The service deliberately does not access the database or storage.
    It receives already-prepared comparison data, which keeps the
    decision logic deterministic and easy to test.
    """

    LOCATION_WEIGHT = 0.45
    TIME_WEIGHT = 0.20
    VISUAL_WEIGHT = 0.35

    def assess(
        self,
        latitude_1: float,
        longitude_1: float,
        timestamp_1: datetime,
        latitude_2: float,
        longitude_2: float,
        timestamp_2: datetime,
        embedding_1: np.ndarray | None = None,
        embedding_2: np.ndarray | None = None,
    ) -> DuplicateAssessment:
        """
        Compare two incidents using location, time, and optional
        visual evidence.

        Visual embeddings are optional because duplicate detection
        should still work when an image or its embedding is unavailable.
        When visual evidence is absent, we fall back to the original
        location + time scoring model.
        """

        # Calculate geographic separation using real Earth-surface
        # distance rather than treating latitude/longitude as x/y values.
        distance = haversine_distance_meters(
            latitude_1,
            longitude_1,
            latitude_2,
            longitude_2,
        )

        # Calculate how close the two reports are in time.
        time_difference = time_difference_hours(
            timestamp_1,
            timestamp_2,
        )

        # Convert the raw geographic and temporal measurements into
        # normalized 0-100 similarity scores.
        location_score = self._location_score(distance)
        time_score = self._time_score(time_difference)

        # A visual comparison is only valid when both incidents have
        # embeddings. Having exactly one would mean we are comparing
        # incomplete evidence, so fail explicitly instead of silently
        # falling back to location and time.
        if (embedding_1 is None) != (embedding_2 is None):
            raise ValueError(
                "Both embeddings must be provided or both must be absent"
            )
        # Visual similarity is an additional signal, not a hard
        # requirement. Both embeddings must be present before we
        # attempt cosine similarity.
        visual_evidence_available = (
            
            embedding_1 is not None
            and embedding_2 is not None
            
        )

        if visual_evidence_available:
            visual_similarity = cosine_similarity(
                embedding_1,
                embedding_2,
            )

            visual_score = self._visual_score(
                visual_similarity
            )

            # With visual evidence available, combine all three signals.
            score = round(
                (
                    location_score * self.LOCATION_WEIGHT
                    + time_score * self.TIME_WEIGHT
                    + visual_score * self.VISUAL_WEIGHT
                ),
                2,
            )

            # Include the visual signal in the explanation so operators
            # can understand why the incidents were considered similar.
            reasons = [
                f"Location similarity score: {location_score:.1f}",
                f"Time similarity score: {time_score:.1f}",
                f"Visual similarity score: {visual_score:.1f}",
                f"Visual cosine similarity: {visual_similarity:.3f}",
            ]

        else:
            # Preserve the original location + time behavior when visual
            # evidence is unavailable. The original model used 60%
            # location and 40% time, so existing behavior remains stable.
            score = round(
                location_score * 0.60
                + time_score * 0.40,
                2,
            )

            # Keep the original two explanations when visual evidence
            # was not available, preserving the existing service contract.
            reasons = [
                f"{distance:.1f} m apart",
                f"{time_difference:.1f} hours apart",
            ]

        # Convert the combined evidence score into the final
        # duplicate/related/separate classification.
        status = self._score_to_status(score)

        return DuplicateAssessment(
            status=status,
            score=score,
            distance_meters=distance,
            time_difference_hours=time_difference,
            location_score=location_score,
            time_score=time_score,
            visual_score=(
                visual_score
                if visual_evidence_available
                else 0.0
            ),
            reasons=reasons,
        )

    @staticmethod
    def _location_score(distance_meters: float) -> float:
        """
        Convert physical distance into a 0-100 similarity score.
        """

        if distance_meters <= 20:
            return 100.0

        if distance_meters <= 50:
            return 70.0

        if distance_meters <= 100:
            return 30.0

        return 0.0

    @staticmethod
    def _time_score(time_difference_hours_value: float) -> float:
        """
        Convert temporal proximity into a 0-100 similarity score.
        """

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
    def _visual_score(similarity: float) -> float:
        """
        Convert cosine similarity into the service's 0-100 scale.

        Our benchmark showed that approximately 0.82 was a useful
        initial separation point for the selected embedding model.

        We deliberately keep this threshold configurable through a
        dedicated method so it can later be recalibrated using real
        CivicLens duplicate examples.
        """

        if not -1.0 <= similarity <= 1.0:
            raise ValueError(
                "Cosine similarity must be between -1.0 and 1.0"
            )

        # The benchmark threshold of 0.82 is treated as strong visual
        # evidence rather than an unconditional duplicate decision.
        if similarity >= 0.82:
            return 100.0

        if similarity >= 0.70:
            return 70.0

        if similarity >= 0.50:
            return 40.0

        return 0.0

    @staticmethod
    def _score_to_status(score: float) -> DuplicateStatus:
        """
        Convert the combined evidence score into a final status.
        """

        if score >= 80:
            return DuplicateStatus.DUPLICATE

        if score >= 50:
            return DuplicateStatus.RELATED

        return DuplicateStatus.SEPARATE