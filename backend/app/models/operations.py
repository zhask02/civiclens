from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Enum as SQLAlchemyEnum
from app.db.database import Base
from app.enums.incident import AuthorityType, IncidentStatus

class Authority(Base):
    __tablename__ = "authorities"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    authority_type: Mapped[AuthorityType] = mapped_column(SQLAlchemyEnum(AuthorityType, values_callable=lambda e:[x.value for x in e]), index=True)
    jurisdiction: Mapped[str] = mapped_column(String, index=True)
    routing_key: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    official_channel: Mapped[str | None] = mapped_column(String, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class RoutingDecision(Base):
    __tablename__ = "routing_decisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), unique=True, index=True)
    authority_id: Mapped[int | None] = mapped_column(ForeignKey("authorities.id"), nullable=True, index=True)
    jurisdiction: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[str] = mapped_column(String, nullable=False)
    manual_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class IncidentAssignment(Base):
    __tablename__ = "incident_assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), unique=True, index=True)
    assigned_to: Mapped[str] = mapped_column(String, nullable=False)
    assigned_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class OperatorNote(Base):
    __tablename__ = "operator_notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    author: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

class IncidentStatusHistory(Base):
    __tablename__ = "incident_status_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    previous_status: Mapped[IncidentStatus] = mapped_column(SQLAlchemyEnum(IncidentStatus, values_callable=lambda e:[x.value for x in e]))
    new_status: Mapped[IncidentStatus] = mapped_column(SQLAlchemyEnum(IncidentStatus, values_callable=lambda e:[x.value for x in e]), index=True)
    actor: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, default="operator")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
