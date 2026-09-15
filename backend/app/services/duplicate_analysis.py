from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.evidence import IncidentEvidence
from app.models.incident import Incident
from app.services.duplicate import (
    DuplicateAssessment,
    DuplicateService,
)
from app.services.duplicate_candidates import (
    DuplicateCandidateService,
)
from app.services.visual_embedding import (
    VisualEmbeddingService,
)
from app.services.storage import download_evidence_file


@dataclass
class DuplicateCandidateAssessment:
    """
    Store the duplicate comparison result for one candidate incident.

    We keep the incident ID beside the assessment so the API can later
    tell the user which existing report was considered similar.
    """

    incident_id: int
    assessment: DuplicateAssessment


@dataclass
class DuplicateAnalysisResult:
    """
    Store the results of comparing an incident against its candidates.
    """

    candidates: list[DuplicateCandidateAssessment]

    @property
    def best_match(self) -> DuplicateCandidateAssessment | None:
        """
        Return the candidate with the highest duplicate score.

        DuplicateService already produces the comparison score, so this
        layer only needs to select the strongest candidate.
        """

        if not self.candidates:
            return None

        return max(
            self.candidates,
            key=lambda candidate: candidate.assessment.score,
        )


class DuplicateAnalysisService:
    """
    Orchestrate the complete duplicate-detection workflow.

    This service connects the existing components without moving their
    responsibilities into one another:

        Candidate retrieval
              ↓
        Evidence retrieval
              ↓
        Image download
              ↓
        Visual embedding
              ↓
        Duplicate comparison
    """

    def __init__(
        self,
        candidate_service: DuplicateCandidateService | None = None,
        duplicate_service: DuplicateService | None = None,
        embedding_service: VisualEmbeddingService | None = None,
        downloader=download_evidence_file,
    ) -> None:
        # Dependency injection lets our tests replace database/storage/ML
        # operations with lightweight fake implementations.
        self.candidate_service = (
            candidate_service
            or DuplicateCandidateService()
        )

        self.duplicate_service = (
            duplicate_service
            or DuplicateService()
        )

        self.embedding_service = (
            embedding_service
            or VisualEmbeddingService()
        )

        # Storage access stays behind the existing storage abstraction.
        # Production therefore uses Supabase automatically, while tests can
        # still inject a fake downloader.
        self.downloader = downloader

    def analyze(
        self,
        db: Session,
        *,
        incident_id: int,
        evidence_id: int,
    ) -> DuplicateAnalysisResult:
        """
        Compare one incident against plausible existing incidents.

        The supplied evidence image represents the incident being
        analyzed. Candidate incidents use their most recent evidence.
        """

        # Load the incident from the existing SQLAlchemy session.
        incident = db.get(Incident, incident_id)

        if incident is None:
            raise ValueError("Incident not found")

        # Load the evidence that belongs to the incident being analyzed.
        evidence = db.get(IncidentEvidence, evidence_id)

        if evidence is None:
            raise ValueError("Evidence not found")

        # Prevent an evidence record belonging to another incident from
        # accidentally being used in this duplicate comparison.
        if evidence.incident_id != incident_id:
            raise ValueError(
                "Evidence does not belong to the incident"
            )

        # Candidate retrieval happens before visual embedding because
        # location/time filtering is much cheaper than running the neural
        # network on every existing incident.
        candidates = self.candidate_service.find_candidates(
            db,
            latitude=incident.latitude,
            longitude=incident.longitude,
            created_at=incident.created_at,
            exclude_incident_id=incident.id,
        )

        # No nearby/recent pothole candidates means there is nothing to
        # compare against.
        if not candidates:
            return DuplicateAnalysisResult(
                candidates=[],
            )

        if self.downloader is None:
            raise RuntimeError(
                "A downloader must be provided for duplicate analysis"
            )

        # Download the new incident's evidence once. Its embedding can
        # then be reused for every candidate comparison.
        new_image_bytes = self.downloader(
            evidence.storage_path,
        )

        new_embedding = self.embedding_service.embed(
            new_image_bytes,
        )

        results: list[DuplicateCandidateAssessment] = []

        for candidate in candidates:
            # Candidate incidents can have multiple evidence records.
            # For now we use the most recently uploaded image as the
            # candidate's representative visual evidence.
            candidate_evidence = (
                db.query(IncidentEvidence)
                .filter(
                    IncidentEvidence.incident_id
                    == candidate.id
                )
                .order_by(
                    IncidentEvidence.created_at.desc()
                )
                .first()
            )

            # A candidate without image evidence cannot receive a visual
            # comparison, so skip it rather than inventing visual evidence.
            if candidate_evidence is None:
                continue

            # Download the candidate's stored image.
            candidate_image_bytes = self.downloader(
                candidate_evidence.storage_path,
            )

            # Generate the candidate's visual representation.
            candidate_embedding = (
                self.embedding_service.embed(
                    candidate_image_bytes,
                )
            )

            # DuplicateService owns the actual mathematical scoring and
            # classification rules. This service only supplies the inputs.
            assessment = self.duplicate_service.assess(
                latitude_1=incident.latitude,
                longitude_1=incident.longitude,
                timestamp_1=incident.created_at,
                latitude_2=candidate.latitude,
                longitude_2=candidate.longitude,
                timestamp_2=candidate.created_at,
                embedding_1=new_embedding,
                embedding_2=candidate_embedding,
            )

            results.append(
                DuplicateCandidateAssessment(
                    incident_id=candidate.id,
                    assessment=assessment,
                )
            )

        return DuplicateAnalysisResult(
            candidates=results,
        )