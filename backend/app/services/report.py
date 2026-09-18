"""Application-level orchestration for citizen pothole submissions."""

from io import BytesIO
from typing import Callable

from PIL import Image
from sqlalchemy.orm import Session

from app.enums.incident import IncidentStatus
from app.models.evidence import IncidentEvidence
from app.models.incident import Incident
from app.schemas.analysis import (
    CompleteAnalysisResponse,
    DuplicateAnalysisResponse,
)
from app.schemas.report import ReportResponse, ReportSubmission
from app.services.analysis import AnalysisService
from app.services.storage import delete_evidence_file, upload_evidence_file
from app.services.routing import RoutingService


class ReportValidationError(ValueError):
    """A safe, client-actionable report submission error."""


class ReportService:
    """Create, store, analyse, and compare a report as one workflow.

    Database writes are committed only after every analysis stage succeeds.
    Object storage cannot share that transaction, so an uploaded object is
    deleted if a later step fails. In v1, an image with no pothole remains a
    rejected (422) submission; it leaves neither database records nor stored
    evidence behind.
    """

    allowed_content_types = {"image/jpeg", "image/png", "image/webp"}
    max_file_size = 10 * 1024 * 1024

    def __init__(
        self,
        analysis_service: AnalysisService,
        uploader: Callable[[int, bytes, str, str], str] = upload_evidence_file,
        deleter: Callable[[str], None] = delete_evidence_file,
        routing_service: RoutingService | None = None,
    ) -> None:
        self.analysis_service = analysis_service
        self.uploader = uploader
        self.deleter = deleter
        self.routing_service = routing_service or RoutingService()

    @classmethod
    def validate_image(
        cls,
        *,
        file_bytes: bytes,
        content_type: str | None,
        filename: str | None,
    ) -> tuple[str, str]:
        if content_type not in cls.allowed_content_types:
            raise ReportValidationError("Unsupported image type")
        if not file_bytes:
            raise ReportValidationError("Image file is required")
        if len(file_bytes) > cls.max_file_size:
            raise ReportValidationError("File size must be 10 MB or less")

        try:
            with Image.open(BytesIO(file_bytes)) as image:
                image.verify()
        except Exception as exc:
            raise ReportValidationError("Invalid or corrupted image") from exc

        extensions = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
        # The declared filename is untrusted; storage naming follows the
        # already validated MIME type rather than a user-controlled suffix.
        return extensions[content_type], content_type

    def submit(
        self,
        *,
        db: Session,
        description: str,
        latitude: float,
        longitude: float,
        file_bytes: bytes,
        content_type: str | None,
        filename: str | None,
    ) -> ReportResponse:
        submission = ReportSubmission(
            description=description,
            latitude=latitude,
            longitude=longitude,
        )
        extension, file_type = self.validate_image(
            file_bytes=file_bytes,
            content_type=content_type,
            filename=filename,
        )

        storage_path: str | None = None
        try:
            incident = Incident(**submission.model_dump())
            db.add(incident)
            db.flush()

            storage_path = self.uploader(
                incident.id, file_bytes, extension, file_type
            )
            evidence = IncidentEvidence(
                incident_id=incident.id,
                storage_path=storage_path,
                file_type=file_type,
            )
            db.add(evidence)
            db.flush()

            result = self.analysis_service.analyze_evidence(
                db=db, incident_id=incident.id, evidence_id=evidence.id
            )
            analysis = self.analysis_service.persist_analysis(
                db=db, evidence_id=evidence.id, result=result, commit=False
            )
            # This is an internal recommendation, not an external complaint.
            # It shares the report transaction so operator queue data is ready.
            self.routing_service.resolve(db, incident.id, result.location)
            duplicate_result = self.analysis_service.duplicate_analysis_service.analyze(
                db=db, incident_id=incident.id, evidence_id=evidence.id
            )

            duplicate = None
            if duplicate_result.best_match is not None:
                match = duplicate_result.best_match
                duplicate = DuplicateAnalysisResponse(
                    incident_id=match.incident_id,
                    status=match.assessment.status.value,
                    score=match.assessment.score,
                    reasons=match.assessment.reasons,
                )

            incident.category = result.vision.category
            incident.severity = result.severity
            incident.confidence = result.vision.confidence
            incident.status = IncidentStatus.ANALYZED
            db.commit()
            db.refresh(incident)
            db.refresh(evidence)
            db.refresh(analysis)

            return ReportResponse(
                report_id=incident.id,
                incident=incident,
                evidence=evidence,
                analysis=CompleteAnalysisResponse(
                    analysis=analysis,
                    duplicate_analysis=duplicate,
                ),
            )
        except Exception:
            db.rollback()
            if storage_path is not None:
                try:
                    self.deleter(storage_path)
                except Exception:
                    # Cleanup failure must not mask the submission failure.
                    pass
            raise
