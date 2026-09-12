from io import BytesIO
from typing import Callable

from PIL import Image

from sqlalchemy.orm import Session

from app.models.analysis import EvidenceAnalysis
from app.models.incident import Incident
from app.models.evidence import IncidentEvidence
from app.schemas.analysis import AnalysisResult
from app.services.location import LocationContextService
from app.services.pothole_detector import PotholeDetector
from app.services.priority import PriorityEngine
from app.services.severity import SeverityEngine
from app.services.storage import download_evidence_file


class AnalysisService:
    """
    Orchestrates the complete CivicLens evidence-analysis pipeline.

    This service is deliberately responsible for coordinating the
    individual components rather than implementing their internal logic.

    The individual components remain independent:

        Storage -> image bytes
        Detector -> visual evidence
        Severity -> visual severity
        Location -> geographic context
        Priority -> operational urgency

    AnalysisService connects those results into one workflow.
    """

    def __init__(
        self,
        detector: PotholeDetector,
        severity_engine: SeverityEngine | None = None,
        location_service: LocationContextService | None = None,
        priority_engine: PriorityEngine | None = None,
        storage_downloader: Callable[[str], bytes] = download_evidence_file,
    ) -> None:
        """
        Inject the components used by the analysis pipeline.

        Dependency injection is important here because tests can provide
        lightweight fake implementations instead of loading YOLO,
        contacting Nominatim, or downloading real Supabase files.
        """

        # The detector performs the actual pothole vision analysis.
        self.detector = detector

        # These engines contain independent deterministic business logic.
        self.severity_engine = severity_engine or SeverityEngine()
        self.location_service = location_service or LocationContextService()
        self.priority_engine = priority_engine or PriorityEngine()

        # Storage is injected as a function so tests can provide fake
        # image bytes without contacting Supabase.
        self.storage_downloader = storage_downloader

    @staticmethod
    def _get_image_dimensions(image_bytes: bytes) -> tuple[int, int]:
        """
        Read image dimensions from the stored evidence.

        SeverityEngine needs image dimensions to calculate bounding-box
        area ratios. We keep this image-processing detail here rather
        than making the severity engine responsible for file formats.
        """

        try:
            # Open the image only long enough to obtain its dimensions.
            with Image.open(BytesIO(image_bytes)) as image:
                return image.size

        except Exception as exc:
            # Convert image-library errors into a predictable application
            # error rather than exposing implementation-specific exceptions.
            raise ValueError("Invalid or corrupted image") from exc

    def analyze_evidence(
        self,
        db: Session,
        incident_id: int,
        evidence_id: int,
    ) -> AnalysisResult:
        """
        Run the complete analysis pipeline for one piece of evidence.

        The evidence must belong to the specified incident. The incident's
        coordinates provide the geographic input for location analysis.
        """

        # Retrieve the evidence record first so we know which stored image
        # needs to be downloaded.
        evidence = (
            db.query(IncidentEvidence)
            .filter(
                IncidentEvidence.id == evidence_id,
                IncidentEvidence.incident_id == incident_id,
            )
            .first()
        )

        if evidence is None:
            raise ValueError("Evidence not found")

        # Retrieve the incident because its latitude and longitude are
        # required by the location-analysis stage.
        incident = (
            db.query(Incident)
            .filter(Incident.id == incident_id)
            .first()
        )

        if incident is None:
            raise ValueError("Incident not found")

        # Download the original image from Supabase Storage.
        image_bytes = self.storage_downloader(
            evidence.storage_path
        )

        # Determine image dimensions for the severity calculation.
        image_width, image_height = self._get_image_dimensions(
            image_bytes
        )

        # Stage 1: ask the vision model to identify potholes and return
        # structured visual evidence.
        vision_prediction = self.detector.analyze(
            image_bytes
        )

        # CivicLens must not interpret "no detection" as a LOW-severity
        # pothole. There is no pothole to score in that situation.
        if not vision_prediction.detections:
            raise ValueError("No pothole detected")

        # Stage 2: estimate apparent visual severity using the detector's
        # bounding boxes and confidence information.
        severity_assessment = self.severity_engine.assess(
            prediction=vision_prediction,
            image_width=image_width,
            image_height=image_height,
        )

        # A successful detection should always produce a severity.
        # This guard protects the persistence layer from receiving null
        # severity values.
        if severity_assessment.severity is None:
            raise ValueError("Unable to determine pothole severity")

        # Stage 3: obtain geographic context from the incident coordinates.
        location_context = self.location_service.get_context(
            latitude=incident.latitude,
            longitude=incident.longitude,
        )

        # Stage 4: calculate operational priority using severity,
        # geographic context, and detector confidence.
        priority_result = self.priority_engine.calculate(
            severity=severity_assessment.severity,
            civic_context=location_context.civic_context,
            confidence=vision_prediction.confidence,
        )

        # Combine the independent stage outputs into one internal result.
        return AnalysisResult(
            vision=vision_prediction,
            severity=severity_assessment.severity,
            severity_score=severity_assessment.score,
            location=location_context,
            priority_score=priority_result.score,
            priority_level=priority_result.level,
            requires_review=priority_result.requires_review,
        )

    def persist_analysis(
        self,
        db: Session,
        evidence_id: int,
        result: AnalysisResult,
    ) -> EvidenceAnalysis:
        """
        Persist a completed analysis result in PostgreSQL.

        Keeping persistence separate from the analysis calculation makes
        the pipeline easier to test: one test can verify the calculations,
        while another verifies database persistence.
        """

        # EvidenceAnalysis stores the final structured outputs of the
        # analysis pipeline. Bounding boxes remain inside VisionPrediction
        # for now because they are not yet persisted separately.
        analysis = EvidenceAnalysis(
            evidence_id=evidence_id,
            category=result.vision.category,
            severity=result.severity,
            confidence=result.vision.confidence,
            model_name=result.vision.model_name,
            severity_score=result.severity_score,
            priority_score=result.priority_score,
            priority_level=result.priority_level,
            requires_review=result.requires_review,
        )

        # Add the new analysis to the current database transaction.
        db.add(analysis)

        # Commit so the analysis becomes durable in PostgreSQL.
        db.commit()

        # Refresh so fields generated by the database, such as the ID
        # and creation timestamp, are available on the returned object.
        db.refresh(analysis)

        return analysis

    def analyze_and_persist(
        self,
        db: Session,
        incident_id: int,
        evidence_id: int,
    ) -> EvidenceAnalysis:
        """
        Run the analysis pipeline and persist its completed result.

        This is the method the API layer will eventually call.
        """

        # First perform all external/model/business-logic work.
        result = self.analyze_evidence(
            db=db,
            incident_id=incident_id,
            evidence_id=evidence_id,
        )

        # Only persist after the complete analysis succeeds.
        return self.persist_analysis(
            db=db,
            evidence_id=evidence_id,
            result=result,
        )