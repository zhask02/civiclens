from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.enums.incident import IncidentCategory
from app.models.incident import Incident
from app.services.duplicate_candidates import DuplicateCandidateService


def make_incident(
    *,
    incident_id: int,
    latitude: float,
    longitude: float,
    created_at: datetime,
    category: IncidentCategory = IncidentCategory.POTHOLE,
) -> Incident:
    """
    Build an Incident ORM object for database tests.

    Keeping object construction in one helper makes each test focus on
    the candidate-retrieval rule it is actually verifying.
    """

    return Incident(
        id=incident_id,
        description=f"Test incident {incident_id}",
        latitude=latitude,
        longitude=longitude,
        category=category,
        created_at=created_at,
    )


def make_database() -> tuple:
    """
    Create an isolated in-memory SQLite database.

    The real application continues using PostgreSQL. SQLite is used here
    only because these tests need a real SQLAlchemy query without touching
    CivicLens's actual development database.
    """

    engine = create_engine("sqlite:///:memory:")

    # Create the incidents table from the same SQLAlchemy model used
    # by the application.
    Base.metadata.create_all(engine)

    return engine


def test_returns_recent_nearby_pothole():
    """
    A pothole within 100 m and within 72 hours should be a candidate.
    """

    engine = make_database()

    now = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)

    with Session(engine) as db:
        db.add(
            make_incident(
                incident_id=1,
                latitude=12.8406,
                longitude=80.1535,
                created_at=now - timedelta(hours=2),
            )
        )
        db.commit()

        service = DuplicateCandidateService()

        candidates = service.find_candidates(
            db,
            latitude=12.8406,
            longitude=80.1534,
            created_at=now,
        )

        assert [incident.id for incident in candidates] == [1]


def test_excludes_incidents_beyond_distance_limit():
    """
    An incident more than 100 m away should not become a candidate,
    even when it was submitted recently.
    """

    engine = make_database()

    now = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)

    with Session(engine) as db:
        db.add(
            make_incident(
                incident_id=1,
                latitude=12.8420,
                longitude=80.1534,
                created_at=now - timedelta(hours=1),
            )
        )
        db.commit()

        service = DuplicateCandidateService()

        candidates = service.find_candidates(
            db,
            latitude=12.8406,
            longitude=80.1534,
            created_at=now,
        )

        assert candidates == []


def test_excludes_old_incidents():
    """
    A nearby pothole older than 72 hours should not be considered a
    duplicate candidate under the current v1 time window.
    """

    engine = make_database()

    now = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)

    with Session(engine) as db:
        db.add(
            make_incident(
                incident_id=1,
                latitude=12.8406,
                longitude=80.1534,
                created_at=now - timedelta(hours=73),
            )
        )
        db.commit()

        service = DuplicateCandidateService()

        candidates = service.find_candidates(
            db,
            latitude=12.8406,
            longitude=80.1534,
            created_at=now,
        )

        assert candidates == []


def test_excludes_non_pothole_incidents():
    """
    CivicLens v1 performs duplicate detection only for potholes, so
    unrelated incident categories must not enter the candidate set.
    """

    engine = make_database()

    now = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)

    with Session(engine) as db:
        db.add(
            make_incident(
                incident_id=1,
                latitude=12.8406,
                longitude=80.1534,
                created_at=now - timedelta(hours=1),
                category=IncidentCategory.GARBAGE,
            )
        )
        db.commit()

        service = DuplicateCandidateService()

        candidates = service.find_candidates(
            db,
            latitude=12.8406,
            longitude=80.1534,
            created_at=now,
        )

        assert candidates == []


def test_excludes_current_incident():
    """
    When the incident already exists in the database, it must not be
    returned as its own duplicate candidate.
    """

    engine = make_database()

    now = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)

    with Session(engine) as db:
        db.add(
            make_incident(
                incident_id=1,
                latitude=12.8406,
                longitude=80.1534,
                created_at=now,
            )
        )
        db.commit()

        service = DuplicateCandidateService()

        candidates = service.find_candidates(
            db,
            latitude=12.8406,
            longitude=80.1534,
            created_at=now,
            exclude_incident_id=1,
        )

        assert candidates == []


def test_returns_multiple_candidates_newest_first():
    """
    Multiple valid candidates should all be returned, with the newest
    report first so downstream duplicate analysis can consider recent
    reports first.
    """

    engine = make_database()

    now = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)

    with Session(engine) as db:
        db.add_all(
            [
                make_incident(
                    incident_id=1,
                    latitude=12.8406,
                    longitude=80.1534,
                    created_at=now - timedelta(hours=5),
                ),
                make_incident(
                    incident_id=2,
                    latitude=12.8407,
                    longitude=80.1534,
                    created_at=now - timedelta(hours=1),
                ),
            ]
        )
        db.commit()

        service = DuplicateCandidateService()

        candidates = service.find_candidates(
            db,
            latitude=12.8406,
            longitude=80.1534,
            created_at=now,
        )

        assert [incident.id for incident in candidates] == [2, 1]