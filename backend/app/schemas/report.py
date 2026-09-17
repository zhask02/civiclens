from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.analysis import AnalysisResponse, CompleteAnalysisResponse
from app.schemas.evidence import EvidenceResponse
from app.schemas.incident import IncidentResponse


class ReportSubmission(BaseModel):
    """Citizen-supplied fields for a pothole report."""

    description: str = Field(min_length=5, max_length=1000)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ReportResponse(BaseModel):
    """The complete result of a successful citizen report submission."""

    report_id: int
    incident: IncidentResponse
    evidence: EvidenceResponse
    analysis: CompleteAnalysisResponse


class ReportListItem(BaseModel):
    """Small citizen-facing report representation for the tracking list."""

    report_id: int
    description: str
    category: str | None
    severity: str | None
    status: str
    created_at: datetime


class ReportDetailResponse(BaseModel):
    """A report plus the latest evidence and persisted assessment."""

    report_id: int
    incident: IncidentResponse
    evidence: EvidenceResponse | None = None
    evidence_url: str | None = None
    analysis: AnalysisResponse | None = None
