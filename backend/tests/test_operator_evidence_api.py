"""API coverage for private evidence access in the operator console."""

from datetime import datetime

from fastapi.testclient import TestClient

from app.api import operator as operator_api
from app.db.dependencies import get_db
from app.main import app
from app.models.evidence import IncidentEvidence
from app.models.incident import Incident
from app.models.analysis import EvidenceAnalysis
from app.models.operations import IncidentAssignment, RoutingDecision
from app.enums.incident import IncidentStatus


class FakeQuery:
    """Provide the small SQLAlchemy query chain used by this endpoint."""

    def __init__(self, result):
        self.result = result

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def first(self):
        return self.result


class FakeOperatorDB:
    def __init__(self, incident, evidence):
        self.incident = incident
        self.evidence = evidence

    def query(self, model):
        return FakeQuery(self.incident if model is Incident else self.evidence)

    def get(self, model, identifier):
        return self.incident if model is Incident and identifier == self.incident.id else None


class FakeResponseQuery:
    """Support the query chain used to assemble operator queue data."""

    def __init__(self, result):
        self.result = result

    def join(self, *args):
        return self

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def first(self):
        return self.result


def test_operator_response_includes_persisted_priority_level():
    """The console receives the analysis priority, not a frontend estimate."""

    incident = Incident(
        id=7,
        description="Pothole near gate",
        latitude=12.9,
        longitude=80.2,
        status=IncidentStatus.SUBMITTED,
        created_at=datetime(2026, 10, 4),
    )
    analysis = type("Analysis", (), {"priority_level": "high"})()

    class ResponseDB:
        def query(self, model):
            results = {
                EvidenceAnalysis: analysis,
                RoutingDecision: None,
                IncidentAssignment: None,
            }
            return FakeResponseQuery(results[model])

    response = operator_api._operator_response(ResponseDB(), incident)

    assert response.priority_level == "high"


def test_operator_can_get_a_signed_url_for_latest_evidence(monkeypatch):
    """Signed URLs are issued only after the router's bearer auth succeeds."""

    incident = type("Incident", (), {"id": 7})()
    evidence = IncidentEvidence(
        id=3,
        incident_id=7,
        storage_path="incidents/7/photo.jpg",
        file_type="image/jpeg",
        created_at=datetime(2026, 9, 18),
    )
    monkeypatch.setenv("CIVICLENS_OPERATOR_TOKEN", "operator-test-token")
    signed_url = "https://storage.example.test/signed-photo"
    monkeypatch.setattr(operator_api, "create_evidence_signed_url", lambda path: signed_url)
    app.dependency_overrides[get_db] = lambda: FakeOperatorDB(incident, evidence)

    try:
        response = TestClient(app).get(
            "/operator/incidents/7/evidence",
            headers={"Authorization": "Bearer operator-test-token"},
        )

        assert response.status_code == 200
        assert response.json() == {"url": signed_url}
    finally:
        app.dependency_overrides.clear()


def test_operator_evidence_requires_bearer_auth():
    """The private URL endpoint cannot be used through public report APIs."""

    response = TestClient(app).get("/operator/incidents/7/evidence")

    assert response.status_code == 401


def test_operator_evidence_reports_missing_image(monkeypatch):
    """The UI can distinguish a valid incident with no uploaded image."""

    incident = type("Incident", (), {"id": 7})()
    monkeypatch.setenv("CIVICLENS_OPERATOR_TOKEN", "operator-test-token")
    app.dependency_overrides[get_db] = lambda: FakeOperatorDB(incident, None)

    try:
        response = TestClient(app).get(
            "/operator/incidents/7/evidence",
            headers={"Authorization": "Bearer operator-test-token"},
        )

        assert response.status_code == 200
        assert response.json() == {"url": None}
    finally:
        app.dependency_overrides.clear()
