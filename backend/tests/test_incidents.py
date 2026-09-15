"""
API-level tests for CivicLens incident endpoints.

These tests focus on FastAPI routing and response serialization.
The expensive ML/storage/database work is replaced with small fakes
so the test remains deterministic and does not call external services.
"""

from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app
from app.api import incidents as incidents_api
from app.schemas.analysis import (
    AnalysisResponse,
    CompleteAnalysisResponse,
    DuplicateAnalysisResponse,
)
from app.schemas.priority import PriorityLevel
from app.enums.incident import IncidentSeverity
from app.enums.incident import IncidentStatus


class FakeAnalysisService:
    """
    Fake analysis service used to isolate the HTTP endpoint.

    The real AnalysisService is already tested separately. Here we only
    need to prove that the endpoint calls it and correctly serializes
    the CompleteAnalysisResponse returned by the service.
    """

    def __init__(self, detector):
        # Keep the constructor compatible with the production service.
        self.detector = detector

    def analyze_and_persist(
        self,
        db,
        incident_id: int,
        evidence_id: int,
    ) -> CompleteAnalysisResponse:
        # Return a realistic successful response so FastAPI must validate
        # and serialize the complete nested response model.
        analysis = AnalysisResponse(
            id=1,
            evidence_id=evidence_id,
            category="pothole",
            severity=IncidentSeverity.HIGH,
            confidence=0.91,
            model_name="test-model",
            severity_score=75.0,
            priority_score=75.0,
            priority_level=PriorityLevel.HIGH,
            requires_review=False,
            created_at=datetime(2026, 9, 16, 12, 0, 0),
        )

        duplicate = DuplicateAnalysisResponse(
            incident_id=41,
            status="related",
            score=67.5,
            reasons=[
                "Nearby incident found",
                "Evidence images are visually similar",
            ],
        )

        return CompleteAnalysisResponse(
            analysis=analysis,
            duplicate_analysis=duplicate,
        )


class FakeDetector:
    """
    Lightweight detector replacement.

    The API endpoint only needs to be able to construct a detector before
    passing it to AnalysisService, so no actual ML model is loaded.
    """

    def __init__(self, model_path):
        # Store the path so the test can confirm construction succeeded.
        self.model_path = model_path

class FakeIncidentQuery:
    """
    Minimal database-query fake for testing the incident endpoint.

    The real endpoint uses SQLAlchemy's query/filter/first chain.
    This fake reproduces only that small interface so the test can
    exercise the HTTP route without requiring a real database.
    """

    def __init__(self, incident):
        self.incident = incident

    def filter(self, *args):
        # The endpoint's filter expression is handled by returning the
        # incident supplied by the test.
        return self

    def first(self):
        # Return the fake incident exactly as a real query would return
        # the matching database record.
        return self.incident


class FakeIncidentDB:
    """
    Minimal database session fake for incident lifecycle API tests.
    """

    def __init__(self, incident):
        self.incident = incident

    def query(self, model):
        # Return a query object containing our controlled test incident.
        return FakeIncidentQuery(self.incident)

    def commit(self):
        # The test does not need real persistence.
        pass

    def refresh(self, incident):
        # The endpoint refreshes the object after committing.
        # Nothing needs to happen in the fake database.
        pass

def test_analysis_endpoint_returns_complete_analysis_response(monkeypatch):
    """
    Verify that the analysis endpoint exposes both analysis results and
    duplicate-analysis results through the public API response schema.
    """

    # Replace the real model-path lookup so the test does not depend on
    # the local ML weights or environment configuration.
    monkeypatch.setattr(
        incidents_api,
        "get_pothole_model_path",
        lambda: "fake-model.pt",
    )

    # Replace the real YOLO detector so this API test never loads the
    # actual pothole model.
    monkeypatch.setattr(
        incidents_api,
        "PotholeDetector",
        FakeDetector,
    )

    # Replace the real analysis service so this test does not touch
    # Supabase, Redis, Nominatim, or the database.
    monkeypatch.setattr(
        incidents_api,
        "AnalysisService",
        FakeAnalysisService,
    )

    # Override the database dependency because the fake service does
    # not need a real SQLAlchemy session for this HTTP-level test.
    app.dependency_overrides[incidents_api.get_db] = lambda: object()

    try:
        # Create a test client against the actual FastAPI application.
        client = TestClient(app)

        response = client.post(
            "/incidents/10/evidence/20/analysis"
        )

        # The route should successfully return the complete response.
        assert response.status_code == 200

        data = response.json()

        # Confirm the persisted evidence analysis is present.
        assert data["analysis"]["id"] == 1
        assert data["analysis"]["evidence_id"] == 20
        assert data["analysis"]["category"] == "pothole"
        assert data["analysis"]["severity"] == "high"
        assert data["analysis"]["priority_level"] == "high"

        # Confirm duplicate analysis is exposed by the API as well.
        assert data["duplicate_analysis"]["incident_id"] == 41
        assert data["duplicate_analysis"]["status"] == "related"
        assert data["duplicate_analysis"]["score"] == 67.5

    finally:
        # Always remove the dependency override so it cannot leak into
        # other tests in the same pytest process.
        app.dependency_overrides.clear()

def test_update_incident_allows_valid_status_transition(monkeypatch):
    """
    Verify that the API allows a status transition that follows the
    CivicLens incident lifecycle.
    """

    incident = type(
        "FakeIncident",
        (),
        {
            "id": 10,
            "description": "Large pothole near the main gate",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "category": None,
            "severity": None,
            "status": IncidentStatus.SUBMITTED,
            "confidence": None,
            "created_at": datetime(2026, 9, 16, 12, 0, 0),
        },
    )()

    app.dependency_overrides[incidents_api.get_db] = (
        lambda: FakeIncidentDB(incident)
    )

    try:
        client = TestClient(app)

        response = client.patch(
            "/incidents/10",
            json={"status": "analyzed"},
        )

        # The transition SUBMITTED → ANALYZED is valid.
        assert response.status_code == 200

        # Confirm that the endpoint actually changed the incident state.
        assert incident.status == IncidentStatus.ANALYZED

        data = response.json()

        # Confirm FastAPI serialized the updated status correctly.
        assert data["status"] == "analyzed"

    finally:
        app.dependency_overrides.clear()


def test_update_incident_rejects_invalid_status_transition():
    """
    Verify that the API rejects a transition that skips lifecycle stages.
    """

    incident = type(
        "FakeIncident",
        (),
        {
            "id": 10,
            "description": "Large pothole near the main gate",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "category": None,
            "severity": None,
            "status": IncidentStatus.SUBMITTED,
            "confidence": None,
            "created_at": datetime(2026, 9, 16, 12, 0, 0),
        },
    )()

    app.dependency_overrides[incidents_api.get_db] = (
        lambda: FakeIncidentDB(incident)
    )

    try:
        client = TestClient(app)

        response = client.patch(
            "/incidents/10",
            json={"status": "resolved"},
        )

        # SUBMITTED → RESOLVED skips ANALYZED, ASSIGNED, and IN_PROGRESS.
        assert response.status_code == 400

        assert "Invalid status transition" in response.json()["detail"]

        # Make sure the invalid request did not mutate the incident.
        assert incident.status == IncidentStatus.SUBMITTED

    finally:
        app.dependency_overrides.clear()

def test_update_incident_does_not_accept_ai_generated_fields():
    """
    Verify that clients cannot manually update AI-generated fields.

    Category, severity, and confidence are produced by the analysis
    pipeline. The incident PATCH API should therefore ignore/reject
    those fields rather than allowing a client to overwrite them.
    """

    incident = type(
        "FakeIncident",
        (),
        {
            "id": 10,
            "description": "Large pothole near the main gate",
            "latitude": 12.9716,
            "longitude": 77.5946,
            "category": None,
            "severity": None,
            "status": IncidentStatus.SUBMITTED,
            "confidence": None,
            "created_at": datetime(2026, 9, 16, 12, 0, 0),
        },
    )()

    app.dependency_overrides[incidents_api.get_db] = (
        lambda: FakeIncidentDB(incident)
    )

    try:
        client = TestClient(app)

        response = client.patch(
            "/incidents/10",
            json={
                "severity": "critical",
                "confidence": 0.99,
            },
        )

        # The request contains no fields accepted by IncidentUpdate,
        # so the endpoint should not modify the incident.
        assert response.status_code == 200

        assert incident.severity is None
        assert incident.confidence is None

        data = response.json()

        assert data["severity"] is None
        assert data["confidence"] is None

    finally:
        app.dependency_overrides.clear()