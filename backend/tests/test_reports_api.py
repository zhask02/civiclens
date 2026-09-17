"""API tests for the citizen report-tracking read endpoints."""

from datetime import datetime

from fastapi.testclient import TestClient

from app.api import reports as reports_api
from app.enums.incident import (
    IncidentCategory,
    IncidentSeverity,
    IncidentStatus,
    PriorityLevel,
)
from app.main import app
from app.models.analysis import EvidenceAnalysis
from app.models.evidence import IncidentEvidence
from app.models.incident import Incident


class FakeQuery:
    """Small query fake supporting the chains used by the report routes."""

    def __init__(self, values):
        self.values = values

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def all(self):
        return self.values

    def first(self):
        return self.values[0] if self.values else None


class FakeReportDB:
    def __init__(self, incidents, evidence=None, analyses=None):
        self.values = {
            Incident: incidents,
            IncidentEvidence: evidence or [],
            EvidenceAnalysis: analyses or [],
        }

    def query(self, model):
        return FakeQuery(self.values[model])


def incident(report_id=8):
    return Incident(
        id=report_id,
        description="Pothole near the main gate",
        latitude=12.9,
        longitude=80.2,
        category=IncidentCategory.POTHOLE,
        severity=IncidentSeverity.HIGH,
        status=IncidentStatus.IN_PROGRESS,
        confidence=0.91,
        created_at=datetime(2026, 9, 16, 12, 0, 0),
    )


def test_lists_persisted_reports_for_tracking():
    app.dependency_overrides[reports_api.get_db] = lambda: FakeReportDB([incident()])
    try:
        response = TestClient(app).get("/reports")
        assert response.status_code == 200
        assert response.json() == [{
            "report_id": 8,
            "description": "Pothole near the main gate",
            "category": "pothole",
            "severity": "high",
            "status": "in_progress",
            "created_at": "2026-09-16T12:00:00",
        }]
    finally:
        app.dependency_overrides.clear()


def test_returns_real_evidence_analysis_and_lifecycle(monkeypatch):
    report = incident()
    evidence = IncidentEvidence(
        id=3,
        incident_id=8,
        storage_path="incidents/8/photo.jpg",
        file_type="image/jpeg",
        created_at=datetime(2026, 9, 16, 12, 1, 0),
    )
    analysis = EvidenceAnalysis(
        id=4,
        evidence_id=3,
        category=IncidentCategory.POTHOLE,
        severity=IncidentSeverity.HIGH,
        confidence=0.91,
        model_name="test-model",
        severity_score=75.0,
        priority_score=75.0,
        priority_level=PriorityLevel.HIGH,
        requires_review=False,
        created_at=datetime(2026, 9, 16, 12, 2, 0),
    )
    monkeypatch.setattr(reports_api, "create_evidence_signed_url", lambda path: "https://storage.test/photo")
    app.dependency_overrides[reports_api.get_db] = lambda: FakeReportDB([report], [evidence], [analysis])
    try:
        response = TestClient(app).get("/reports/8")
        assert response.status_code == 200
        data = response.json()
        assert data["report_id"] == 8
        assert data["incident"]["status"] == "in_progress"
        assert data["evidence"]["id"] == 3
        assert data["evidence_url"] == "https://storage.test/photo"
        assert data["analysis"]["severity"] == "high"
        assert data["analysis"]["priority_level"] == "high"
    finally:
        app.dependency_overrides.clear()


def test_returns_not_found_for_an_unknown_report():
    app.dependency_overrides[reports_api.get_db] = lambda: FakeReportDB([])
    try:
        response = TestClient(app).get("/reports/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Report not found"
    finally:
        app.dependency_overrides.clear()
