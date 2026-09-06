from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.types import Enum as SQLAlchemyEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.enums.incident import IncidentCategory, IncidentSeverity


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

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    model_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )