from datetime import datetime, timedelta

import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.models.evidence import IncidentEvidence
from app.models.incident import Incident
from app.services.duplicate import DuplicateStatus
from app.services.duplicate_analysis import DuplicateAnalysisService
from app.enums.incident import IncidentCategory

class FakeEmbeddingService:
    """
    Return predetermined embeddings instead of loading MobileNetV3.

    This keeps the tests fast and makes them independent of the actual
    neural-network model.
    """

    def embed(self, image_bytes: bytes) -> np.ndarray:
        # Use different vectors for different fake image identifiers so
        # the test can control which candidates look visually similar.
        if image_bytes == b"new-image":
            return np.array([1.0, 0.0, 0.0])

        if image_bytes == b"same-image":
            return np.array([1.0, 0.0, 0.0])

        return np.array([0.0, 1.0, 0.0])


class FakeDownloader:
    """
    Return fake image bytes based on a storage path.

    No real Supabase Storage request is made during testing.
    """

    def __call__(self, storage_path: str) -> bytes:
        # The storage path identifies which fake image should be returned.
        if storage_path == "new.jpg":
            return b"new-image"

        if storage_path == "same.jpg":
            return b"same-image"

        return b"different-image"


def make_database():
    """
    Create an isolated in-memory SQLite database for each test.

    Using an in-memory database means the tests do not modify CivicLens'
    real database.
    """

    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)

    return engine


def add_incident(
    db: Session,
    *,
    description: str,
    latitude: float,
    longitude: float,
    created_at: datetime,
) -> Incident:
    """
    Insert a test incident into the temporary database.
    """

    incident = Incident(
        description=description,
        latitude=latitude,
        longitude=longitude,
        # Candidate retrieval intentionally searches only pothole incidents,
        # so our duplicate-analysis fixtures must represent pothole reports.
        category=IncidentCategory.POTHOLE,
        created_at=created_at,
    )

    db.add(incident)
    db.commit()
    db.refresh(incident)

    return incident


def add_evidence(
    db: Session,
    *,
    incident_id: int,
    storage_path: str,
) -> IncidentEvidence:
    """
    Insert a test evidence record for an incident.
    """

    evidence = IncidentEvidence(
        incident_id=incident_id,
        storage_path=storage_path,
        file_type="image/jpeg",
    )

    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    return evidence


def make_service() -> DuplicateAnalysisService:
    """
    Create the orchestration service with fake external dependencies.

    The real DuplicateService is retained because its deterministic
    scoring logic is exactly what we want to exercise.
    """

    return DuplicateAnalysisService(
        embedding_service=FakeEmbeddingService(),
        downloader=FakeDownloader(),
    )


def test_returns_empty_result_when_no_candidates_exist():
    """
    An incident with no nearby/recent pothole candidates should produce
    an empty duplicate-analysis result.
    """

    engine = make_database()

    with Session(engine) as db:
        incident = add_incident(
            db,
            description="New pothole",
            latitude=12.8406,
            longitude=80.1534,
            created_at=datetime(2026, 9, 15, 10, 0, 0),
        )

        evidence = add_evidence(
            db,
            incident_id=incident.id,
            storage_path="new.jpg",
        )

        service = make_service()

        result = service.analyze(
            db,
            incident_id=incident.id,
            evidence_id=evidence.id,
        )

        assert result.candidates == []
        assert result.best_match is None


def test_compares_new_incident_against_candidate():
    """
    A nearby and recent incident with evidence should be compared using
    location, time, and visual similarity.
    """

    engine = make_database()

    with Session(engine) as db:
        # Create the older report first because the new report must be
        # able to find it during candidate retrieval.
        candidate = add_incident(
            db,
            description="Existing pothole",
            latitude=12.8407,
            longitude=80.1535,
            created_at=datetime(2026, 9, 15, 9, 30, 0),
        )

        add_evidence(
            db,
            incident_id=candidate.id,
            storage_path="same.jpg",
        )

        new_incident = add_incident(
            db,
            description="New pothole report",
            latitude=12.8406,
            longitude=80.1534,
            created_at=datetime(2026, 9, 15, 10, 0, 0),
        )

        new_evidence = add_evidence(
            db,
            incident_id=new_incident.id,
            storage_path="new.jpg",
        )

        service = make_service()

        result = service.analyze(
            db,
            incident_id=new_incident.id,
            evidence_id=new_evidence.id,
        )

        assert len(result.candidates) == 1

        comparison = result.candidates[0]

        assert comparison.incident_id == candidate.id

        # Both fake images produce the same embedding, so the visual
        # similarity should receive the maximum visual score.
        assert comparison.assessment.visual_score == 100.0

        # The two reports are very close in both location and time, so
        # the combined score should classify them as duplicates.
        assert comparison.assessment.status == DuplicateStatus.DUPLICATE
        assert result.best_match is comparison


def test_skips_candidate_without_evidence():
    """
    A geographically and temporally plausible candidate without image
    evidence should not be visually compared.
    """

    engine = make_database()

    with Session(engine) as db:
        candidate = add_incident(
            db,
            description="Existing pothole without image",
            latitude=12.8407,
            longitude=80.1535,
            created_at=datetime(2026, 9, 15, 9, 30, 0),
        )

        new_incident = add_incident(
            db,
            description="New pothole report",
            latitude=12.8406,
            longitude=80.1534,
            created_at=datetime(2026, 9, 15, 10, 0, 0),
        )

        new_evidence = add_evidence(
            db,
            incident_id=new_incident.id,
            storage_path="new.jpg",
        )

        service = make_service()

        result = service.analyze(
            db,
            incident_id=new_incident.id,
            evidence_id=new_evidence.id,
        )

        # The candidate was retrieved but skipped because it has no
        # evidence image available for visual comparison.
        assert result.candidates == []


def test_rejects_evidence_belonging_to_another_incident():
    """
    Evidence must belong to the incident being analyzed.

    This protects the workflow from accidentally comparing an incident
    against an unrelated evidence record.
    """

    engine = make_database()

    with Session(engine) as db:
        incident_1 = add_incident(
            db,
            description="First pothole",
            latitude=12.8406,
            longitude=80.1534,
            created_at=datetime(2026, 9, 15, 10, 0, 0),
        )

        incident_2 = add_incident(
            db,
            description="Second pothole",
            latitude=12.8506,
            longitude=80.1634,
            created_at=datetime(2026, 9, 15, 10, 0, 0),
        )

        evidence = add_evidence(
            db,
            incident_id=incident_2.id,
            storage_path="same.jpg",
        )

        service = make_service()

        try:
            service.analyze(
                db,
                incident_id=incident_1.id,
                evidence_id=evidence.id,
            )
            assert False, "Expected ValueError"
        except ValueError as exc:
            assert str(exc) == "Evidence does not belong to the incident"


def test_selects_strongest_candidate_as_best_match():
    """
    When multiple candidates are available, best_match should return
    whichever comparison receives the highest duplicate score.
    """

    engine = make_database()

    with Session(engine) as db:
        strong_candidate = add_incident(
            db,
            description="Strong candidate",
            latitude=12.8407,
            longitude=80.1535,
            created_at=datetime(2026, 9, 15, 9, 30, 0),
        )

        add_evidence(
            db,
            incident_id=strong_candidate.id,
            storage_path="same.jpg",
        )

        # Keep the weaker candidate inside the 100 m retrieval radius.
        # It will still receive a lower duplicate score because its image and
        # timestamp are less similar to the new report.
        weaker_candidate = add_incident(
            db,
            description="Weaker candidate",
            latitude=12.8410,
            longitude=80.1537,
            created_at=datetime(2026, 9, 15, 7, 0, 0),
        )

        add_evidence(
            db,
            incident_id=weaker_candidate.id,
            storage_path="different.jpg",
        )

        new_incident = add_incident(
            db,
            description="New pothole",
            latitude=12.8406,
            longitude=80.1534,
            created_at=datetime(2026, 9, 15, 10, 0, 0),
        )

        new_evidence = add_evidence(
            db,
            incident_id=new_incident.id,
            storage_path="new.jpg",
        )

        service = make_service()

        result = service.analyze(
            db,
            incident_id=new_incident.id,
            evidence_id=new_evidence.id,
        )

        assert len(result.candidates) == 2

        # The candidate with the matching image and stronger location/time
        # evidence should be selected as the best match.
        assert result.best_match is not None
        assert result.best_match.incident_id == strong_candidate.id