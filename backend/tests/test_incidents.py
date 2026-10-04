"""Release-boundary tests for retired legacy incident paths and lifecycle API."""

from datetime import datetime

from fastapi.testclient import TestClient

from app.db.dependencies import get_db
from app.enums.incident import IncidentStatus
from app.main import app


class FakeStatusDB:
    def __init__(self, incident):
        self.incident = incident
        self.history = []

    def get(self, model, identifier):
        return self.incident if identifier == self.incident.id else None

    def add(self, entry):
        self.history.append(entry)

    def commit(self):
        pass

    def refresh(self, incident):
        pass


def _incident():
    return type("Incident", (), {
        "id": 10,
        "description": "Large pothole near the main gate",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "category": None,
        "severity": None,
        "status": IncidentStatus.SUBMITTED,
        "confidence": None,
        "created_at": datetime(2026, 9, 16, 12, 0, 0),
    })()


def test_legacy_incident_routes_are_not_exposed():
    client = TestClient(app)
    assert client.post("/incidents", json={"description": "Pothole", "latitude": 12.9, "longitude": 80.2}).status_code == 404
    assert client.get("/incidents/10/evidence/20/url").status_code == 404


def test_operator_can_advance_status_and_history_is_recorded(monkeypatch):
    incident = _incident()
    db = FakeStatusDB(incident)
    monkeypatch.setenv("CIVICLENS_OPERATOR_TOKEN", "operator-test-token")
    app.dependency_overrides[get_db] = lambda: db
    try:
        response = TestClient(app).patch(
            "/operator/incidents/10/status",
            json={"status": "analyzed"},
            headers={"Authorization": "Bearer operator-test-token"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "analyzed"
        assert incident.status == IncidentStatus.ANALYZED
        assert db.history[0].previous_status == IncidentStatus.SUBMITTED
        assert db.history[0].new_status == IncidentStatus.ANALYZED
        assert db.history[0].actor == "operator"
        assert db.history[0].source == "operator_api"
    finally:
        app.dependency_overrides.clear()


def test_operator_status_requires_authentication():
    response = TestClient(app).patch("/operator/incidents/10/status", json={"status": "analyzed"})
    assert response.status_code == 401


def test_operator_status_rejects_skipped_transition(monkeypatch):
    incident = _incident()
    monkeypatch.setenv("CIVICLENS_OPERATOR_TOKEN", "operator-test-token")
    app.dependency_overrides[get_db] = lambda: FakeStatusDB(incident)
    try:
        response = TestClient(app).patch(
            "/operator/incidents/10/status",
            json={"status": "resolved"},
            headers={"Authorization": "Bearer operator-test-token"},
        )
        assert response.status_code == 400
        assert "Invalid status transition" in response.json()["detail"]
        assert incident.status == IncidentStatus.SUBMITTED
    finally:
        app.dependency_overrides.clear()
