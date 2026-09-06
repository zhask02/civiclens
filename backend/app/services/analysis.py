from sqlalchemy.orm import Session

from app.models.analysis import EvidenceAnalysis
from app.schemas.analysis import AnalysisCreate


def create_evidence_analysis(
    db: Session,
    evidence_id: int,
    analysis: AnalysisCreate,
) -> EvidenceAnalysis:
    new_analysis = EvidenceAnalysis(
        evidence_id=evidence_id,
        category=analysis.category,
        severity=analysis.severity,
        confidence=analysis.confidence,
        model_name=analysis.model_name,
    )

    db.add(new_analysis)
    db.commit()
    db.refresh(new_analysis)

    return new_analysis