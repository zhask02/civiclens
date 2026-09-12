from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.types import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.enums.incident import (
    IncidentCategory,
    IncidentSeverity,
    PriorityLevel,
)


class EvidenceAnalysis(Base):
    __tablename__ = "evidence_analyses"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("incident_evidence.id"),
        nullable=False,
    )

    category: Mapped[IncidentCategory] = mapped_column(
        SQLAlchemyEnum(
            IncidentCategory,
            values_callable=lambda enum_class: [
                item.value for item in enum_class
            ],
        ),
        nullable=False,
    )

    severity: Mapped[IncidentSeverity] = mapped_column(
        SQLAlchemyEnum(
            IncidentSeverity,
            values_callable=lambda enum_class: [
                item.value for item in enum_class
            ],
        ),
        nullable=False,
    )

    # Confidence describes how strongly the vision model supports
    # the detected category.
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # Model identifier lets us trace which vision model produced
    # this analysis.
    model_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    # Severity score stores the numeric result behind the
    # human-readable IncidentSeverity value.
    severity_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # Priority score represents the operational urgency after
    # considering severity, location, and confidence.
    priority_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # Priority level is intentionally separate from incident severity.
    priority_level: Mapped[PriorityLevel] = mapped_column(
        SQLAlchemyEnum(
            PriorityLevel,
            values_callable=lambda enum_class: [
                item.value for item in enum_class
            ],
        ),
        nullable=False,
    )

    # Flags analyses that should receive human verification,
    # particularly when model confidence is low.
    requires_review: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )