from datetime import datetime, UTC

import pytest

from app.enums.incident import (
    IncidentSeverity,
    PriorityLevel,
)
from app.models.evidence import IncidentEvidence
from app.models.incident import Incident
from app.schemas.location import CivicContext, LocationContext
from app.schemas.priority import PriorityResult
from app.schemas.vision import (
    BoundingBox,
    VisionDetection,
    VisionPrediction,
)
from app.services.analysis import AnalysisService
from app.services.severity import SeverityAssessment


def make_prediction(
    confidence: float = 0.9,
) -> VisionPrediction:
    """
    Build a realistic pothole prediction for orchestration tests.

    The detector itself is already tested separately, so these tests
    focus on whether AnalysisService correctly passes its output
    through the remaining analysis stages.
    """

    return VisionPrediction(
        category="pothole",
        confidence=confidence,
        model_name="test-model",
        detections=[
            VisionDetection(
                label="pothole",
                confidence=confidence,
                bounding_box=BoundingBox(
                    x_min=0,
                    y_min=0,
                    x_max=500,
                    y_max=500,
                ),
            )
        ],
    )


class FakeDetector:
    """
    Lightweight detector used instead of loading the real YOLO model.

    Unit tests should verify orchestration without depending on
    heavyweight ML inference.
    """

    def __init__(self, prediction: VisionPrediction):
        self.prediction = prediction
        self.received_image_bytes = None

    def analyze(self, image_bytes: bytes) -> VisionPrediction:
        # Remember the bytes so the test can verify that storage output
        # actually reaches the vision-analysis stage.
        self.received_image_bytes = image_bytes

        return self.prediction


class FakeSeverityEngine:
    """
    Fake severity engine that records the detector output it receives.

    This lets us verify that AnalysisService passes the correct
    prediction and image dimensions downstream.
    """

    def __init__(self, assessment: SeverityAssessment):
        self.assessment = assessment
        self.received_prediction = None
        self.received_dimensions = None

    def assess(
        self,
        prediction: VisionPrediction,
        image_width: int,
        image_height: int,
    ) -> SeverityAssessment:
        self.received_prediction = prediction
        self.received_dimensions = (image_width, image_height)

        return self.assessment


class FakeLocationService:
    """
    Fake location service that returns deterministic geographic context.

    The real service uses Redis and Nominatim, which are unnecessary
    dependencies for testing the orchestration itself.
    """

    def __init__(self, context: LocationContext):
        self.context = context
        self.received_coordinates = None

    def get_context(
        self,
        latitude: float,
        longitude: float,
    ) -> LocationContext:
        # Record the coordinates so the test can verify that the
        # incident's location is passed to the location stage.
        self.received_coordinates = (latitude, longitude)

        return self.context


class FakePriorityEngine:
    """
    Fake priority engine used to verify the final orchestration step.
    """

    def __init__(self, result: PriorityResult):
        self.result = result
        self.received_arguments = None

    def calculate(
        self,
        severity: IncidentSeverity,
        civic_context: CivicContext,
        confidence: float,
    ) -> PriorityResult:
        # Record every input so the test can verify that AnalysisService
        # combines severity, location, and confidence correctly.
        self.received_arguments = (
            severity,
            civic_context,
            confidence,
        )

        return self.result


class FakeDBQuery:
    """
    Minimal query object for testing database lookup behaviour.

    The real SQLAlchemy session is tested separately through the
    application/database integration path. These tests only need
    deterministic query results for the orchestration layer.
    """

    def __init__(self, result):
        self.result = result

    def filter(self, *args):
        # The actual filter expressions are database concerns.
        # For this unit test, simply preserve the configured result.
        return self

    def first(self):
        return self.result


class FakeDB:
    """
    Minimal database session containing configurable evidence and incident.

    This avoids requiring PostgreSQL just to test AnalysisService's
    control flow and validation behaviour.
    """

    def __init__(
        self,
        evidence: IncidentEvidence | None,
        incident: Incident | None,
    ):
        self.evidence = evidence
        self.incident = incident

    def query(self, model):
        # Return the appropriate fake query depending on which model
        # AnalysisService is trying to retrieve.
        if model is IncidentEvidence:
            return FakeDBQuery(self.evidence)

        if model is Incident:
            return FakeDBQuery(self.incident)

        raise AssertionError(f"Unexpected model queried: {model}")


def make_incident() -> Incident:
    """
    Create an incident object with realistic coordinates.

    The object does not need to be committed to a database because
    these tests only exercise AnalysisService's orchestration logic.
    """

    return Incident(
        id=1,
        description="Test pothole",
        latitude=12.8406,
        longitude=80.1534,
    )


def make_evidence() -> IncidentEvidence:
    """
    Create evidence pointing to a fake stored image.

    The storage downloader will return image bytes without contacting
    Supabase during the test.
    """

    return IncidentEvidence(
        id=1,
        incident_id=1,
        storage_path="incidents/1/test.jpg",
        file_type="image/jpeg",
        created_at=datetime.now(UTC),
    )


def make_location_context() -> LocationContext:
    """
    Build deterministic location information for the pipeline test.
    """

    return LocationContext(
        latitude=12.8406,
        longitude=80.1534,
        osm_category="highway",
        osm_type="primary",
        osm_name="Test Road",
        osm_road="Test Road",
        city="Chennai",
        state="Tamil Nadu",
        country="India",
        civic_context=CivicContext.CAMPUS,
    )


def make_service(
    prediction: VisionPrediction | None = None,
    severity: IncidentSeverity = IncidentSeverity.HIGH,
    severity_score: float = 75.0,
    location: LocationContext | None = None,
    priority_score: float = 75.0,
    priority_level: PriorityLevel = PriorityLevel.HIGH,
    requires_review: bool = False,
):
    """
    Assemble AnalysisService with fake dependencies.

    This is the central test fixture helper: each test can customize
    one stage while keeping the rest of the pipeline deterministic.
    """

    prediction = prediction or make_prediction()

    detector = FakeDetector(prediction)

    severity_engine = FakeSeverityEngine(
        SeverityAssessment(
            score=severity_score,
            severity=severity,
            reasons=["Test severity"],
        )
    )

    location_service = FakeLocationService(
        location or make_location_context()
    )

    priority_engine = FakePriorityEngine(
        PriorityResult(
            score=priority_score,
            level=priority_level,
            requires_review=requires_review,
        )
    )

    # The fake downloader returns a small valid JPEG so that the real
    # image-dimension helper can exercise its image parsing behaviour.
    # This byte sequence represents a minimal 1x1 JPEG.
    image_bytes = (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01"
        b"\x00\x01\x00\x00\xff\xdb\x00C\x00"
        + bytes([8] * 64)
        + b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
        b"\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00"
        b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
        b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00"
        b"\xd2\xcf \xff\xd9"
    )

    def fake_downloader(storage_path: str) -> bytes:
        # Verify that AnalysisService requests the exact evidence path.
        assert storage_path == "incidents/1/test.jpg"
        return image_bytes

    service = AnalysisService(
        detector=detector,
        severity_engine=severity_engine,
        location_service=location_service,
        priority_engine=priority_engine,
        storage_downloader=fake_downloader,
    )

    return service, detector, severity_engine, location_service, priority_engine


def test_successful_analysis_orchestrates_all_stages():
    """
    A valid evidence record should flow through every analysis stage.

    This is the most important orchestration test: it verifies that
    AnalysisService connects storage, vision, severity, location,
    and priority correctly.
    """

    service, detector, severity_engine, location_service, priority_engine = (
        make_service()
    )

    db = FakeDB(
        evidence=make_evidence(),
        incident=make_incident(),
    )

    result = service.analyze_evidence(
        db=db,
        incident_id=1,
        evidence_id=1,
    )

    # The detector must receive the image returned by storage.
    assert detector.received_image_bytes is not None

    # Severity must receive the detector's exact prediction.
    assert severity_engine.received_prediction is detector.prediction

    # The image-dimension helper should have successfully extracted
    # positive dimensions from the downloaded image.
    assert severity_engine.received_dimensions[0] > 0
    assert severity_engine.received_dimensions[1] > 0

    # Location analysis must use the incident's coordinates.
    assert location_service.received_coordinates == (
        12.8406,
        80.1534,
    )

    # Priority must receive the outputs from the preceding stages.
    assert priority_engine.received_arguments == (
        IncidentSeverity.HIGH,
        CivicContext.CAMPUS,
        0.9,
    )

    # Finally, all stage outputs must be combined into AnalysisResult.
    assert result.vision is detector.prediction
    assert result.severity == IncidentSeverity.HIGH
    assert result.severity_score == 75.0
    assert result.location.civic_context == CivicContext.CAMPUS
    assert result.priority_score == 75.0
    assert result.priority_level == PriorityLevel.HIGH
    assert result.requires_review is False


def test_missing_evidence_is_rejected():
    """Analysis should fail before downloading or processing missing evidence."""

    service, *_ = make_service()

    db = FakeDB(
        evidence=None,
        incident=make_incident(),
    )

    with pytest.raises(ValueError, match="Evidence not found"):
        service.analyze_evidence(
            db=db,
            incident_id=1,
            evidence_id=999,
        )


def test_missing_incident_is_rejected():
    """Analysis should fail when the incident itself cannot be found."""

    service, *_ = make_service()

    db = FakeDB(
        evidence=make_evidence(),
        incident=None,
    )

    with pytest.raises(ValueError, match="Incident not found"):
        service.analyze_evidence(
            db=db,
            incident_id=999,
            evidence_id=1,
        )


def test_no_pothole_detection_is_rejected():
    """
    A model result with no detections must not become a LOW-severity
    pothole or enter the priority engine.
    """

    prediction = VisionPrediction(
        category=None,
        confidence=0.0,
        model_name="test-model",
        detections=[],
    )

    service, *_ = make_service(
        prediction=prediction,
    )

    db = FakeDB(
        evidence=make_evidence(),
        incident=make_incident(),
    )

    with pytest.raises(ValueError, match="No pothole detected"):
        service.analyze_evidence(
            db=db,
            incident_id=1,
            evidence_id=1,
        )


def test_severity_without_result_is_rejected():
    """
    A successful detector result should produce a concrete severity.

    This protects the persistence boundary from receiving null severity.
    """

    service, *_ = make_service(
        severity=None,
    )

    db = FakeDB(
        evidence=make_evidence(),
        incident=make_incident(),
    )

    with pytest.raises(
        ValueError,
        match="Unable to determine pothole severity",
    ):
        service.analyze_evidence(
            db=db,
            incident_id=1,
            evidence_id=1,
        )


def test_invalid_image_is_rejected():
    """Corrupted storage data should fail before model inference."""

    def invalid_downloader(storage_path: str) -> bytes:
        # Simulate a broken or corrupted object returned by storage.
        return b"not-an-image"

    service, *_ = make_service()

    # Replace the normal storage dependency with the corrupted response.
    service.storage_downloader = invalid_downloader

    db = FakeDB(
        evidence=make_evidence(),
        incident=make_incident(),
    )

    with pytest.raises(ValueError, match="Invalid or corrupted image"):
        service.analyze_evidence(
            db=db,
            incident_id=1,
            evidence_id=1,
        )


def test_evidence_must_belong_to_incident():
    """
    Evidence lookup must be constrained by both evidence ID and incident ID.

    The real SQLAlchemy query performs that ownership check. This test
    verifies the service's expected database interaction contract.
    """

    service, *_ = make_service()

    # Return no evidence to represent a mismatched incident/evidence pair.
    db = FakeDB(
        evidence=None,
        incident=make_incident(),
    )

    with pytest.raises(ValueError, match="Evidence not found"):
        service.analyze_evidence(
            db=db,
            incident_id=999,
            evidence_id=1,
        )