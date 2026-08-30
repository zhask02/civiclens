from datetime import datetime 

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.types import Enum as SQLAlchemyEnum

from app.enums.incident import IncidentCategory, IncidentSeverity
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base

class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    category: Mapped[IncidentCategory | None] = mapped_column(
        SQLAlchemyEnum(IncidentCategory, 
                       values_callable=lambda enum_class: [item.value for item in enum_class]), nullable=True
    )
    severity: Mapped[IncidentSeverity | None] = mapped_column(
        SQLAlchemyEnum(IncidentSeverity, 
                       values_callable=lambda enum_class: [item.value for item in enum_class]), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="submitted",
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )