"""Tests for the atomic citizen report-submission workflow."""

from datetime import datetime
from io import BytesIO

import pytest
from PIL import Image

from app.enums.incident import IncidentSeverity, PriorityLevel
from app.models.analysis import EvidenceAnalysis
from app.models.evidence import IncidentEvidence
from app.models.incident import Incident
from app.schemas.analysis import AnalysisResult
from app.schemas.location import LocationContext
from app.schemas.vision import BoundingBox, VisionDetection, VisionPrediction
from app.services.report import ReportService, ReportValidationError


def image_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (8, 8), "black").save(buffer, format="JPEG")
    return buffer.getvalue()


class Query:
    def __init__(self, result): self.result = result
    def filter(self, *args): return self
    def first(self): return self.result


class FakeDB:
    def __init__(self):
        self.incident = self.evidence = self.analysis = None
        self.committed = self.rolled_back = False
    def add(self, obj):
        if isinstance(obj, Incident): self.incident = obj
        elif isinstance(obj, IncidentEvidence): self.evidence = obj
        elif isinstance(obj, EvidenceAnalysis): self.analysis = obj
    def flush(self):
        if self.incident and self.incident.id is None: self.incident.id = 7
        if self.evidence and self.evidence.id is None: self.evidence.id = 9
        if self.analysis and self.analysis.id is None: self.analysis.id = 11
    def query(self, model): return Query(self.evidence if model is IncidentEvidence else self.incident)
    def commit(self): self.committed = True
    def rollback(self): self.rolled_back = True
    def refresh(self, obj):
        if getattr(obj, "created_at", None) is None: obj.created_at = datetime(2026, 9, 16, 12, 0, 0)


class NoDuplicates:
    class Result: best_match = None
    def analyze(self, **kwargs): return self.Result()


class FakeAnalysisService:
    def __init__(self, fail=False):
        self.fail, self.persist_commit = fail, None
        self.duplicate_analysis_service = NoDuplicates()
    def analyze_evidence(self, **kwargs):
        if self.fail: raise ValueError("No pothole detected")
        return AnalysisResult(
            vision=VisionPrediction(category="pothole", confidence=0.91, model_name="test-model", detections=[VisionDetection(label="pothole", confidence=0.91, bounding_box=BoundingBox(x_min=0, y_min=0, x_max=5, y_max=5))]),
            severity=IncidentSeverity.HIGH, severity_score=75.0,
            location=LocationContext(latitude=12.9, longitude=80.2),
            priority_score=75.0, priority_level=PriorityLevel.HIGH, requires_review=False,
        )
    def persist_analysis(self, *, db, evidence_id, result, commit):
        self.persist_commit = commit
        analysis = EvidenceAnalysis(evidence_id=evidence_id, category="pothole", severity=result.severity, confidence=0.91, model_name="test-model", severity_score=75.0, priority_score=75.0, priority_level=PriorityLevel.HIGH, requires_review=False)
        db.add(analysis); db.flush()
        return analysis


def make_service(analysis=None, uploads=None, deleted=None):
    uploads = uploads if uploads is not None else []
    deleted = deleted if deleted is not None else []
    return ReportService(analysis or FakeAnalysisService(), uploader=lambda incident_id, content, extension, content_type: (uploads.append((incident_id, content, extension, content_type)) or "incidents/7/image.jpg"), deleter=deleted.append)


def test_submit_report_creates_and_analyzes_one_atomic_report():
    db, uploads, analysis = FakeDB(), [], FakeAnalysisService()
    response = make_service(analysis, uploads).submit(db=db, description="Large pothole near main gate", latitude=12.9, longitude=80.2, file_bytes=image_bytes(), content_type="image/jpeg", filename="pothole.jpg")
    assert db.committed and not db.rolled_back
    assert uploads and uploads[0][0] == 7
    assert analysis.persist_commit is False
    assert response.report_id == 7
    assert response.incident.status == "analyzed"
    assert response.incident.severity == "high"
    assert response.evidence.incident_id == 7
    assert response.analysis.analysis.evidence_id == 9


def test_failed_analysis_rolls_back_and_deletes_uploaded_evidence():
    db, deleted = FakeDB(), []
    with pytest.raises(ValueError, match="No pothole detected"):
        make_service(FakeAnalysisService(fail=True), deleted=deleted).submit(db=db, description="Large pothole near main gate", latitude=12.9, longitude=80.2, file_bytes=image_bytes(), content_type="image/jpeg", filename="pothole.jpg")
    assert db.rolled_back
    assert deleted == ["incidents/7/image.jpg"]


@pytest.mark.parametrize("content_type,content", [("image/gif", image_bytes()), ("image/jpeg", b"not an image")])
def test_invalid_report_images_are_rejected_before_upload(content_type, content):
    with pytest.raises(ReportValidationError):
        make_service().submit(db=FakeDB(), description="Large pothole near main gate", latitude=12.9, longitude=80.2, file_bytes=content, content_type=content_type, filename="pothole.jpg")
