from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class IncidentEvidence(Base):
    __tablename__ = "incident_evidence"

    id: Mapped[int] = mapped_column(primary_key=True)

    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), nullable=False,)

    file_url: Mapped[str] = mapped_column(String, nullable=False,)

    file_type: Mapped[str] = mapped_column(String, nullable=False,)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False,)