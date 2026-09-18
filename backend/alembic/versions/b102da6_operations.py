"""add operator operations tables

Revision ID: b102da6_operations
Revises: 8a137bfae737
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime
from sqlalchemy.dialects import postgresql
revision = "b102da6_operations"
down_revision = "8a137bfae737"
branch_labels = depends_on = None
def upgrade():
    # Named PostgreSQL enums are created explicitly below. Disabling their
    # table-level DDL prevents create_table from issuing a second CREATE TYPE.
    authority_type = postgresql.ENUM("public_local", "public_state", "national_highway", "campus_private", "unknown", name="authoritytype", create_type=False)
    status = postgresql.ENUM("submitted", "analyzed", "assigned", "in_progress", "resolved", name="incidentstatus", create_type=False)
    authority_type.create(op.get_bind(), checkfirst=True)
    op.create_table("authorities", sa.Column("id",sa.Integer,primary_key=True),sa.Column("name",sa.String,nullable=False,unique=True),sa.Column("authority_type",authority_type,nullable=False),sa.Column("jurisdiction",sa.String,nullable=False),sa.Column("routing_key",sa.String),sa.Column("official_channel",sa.String),sa.Column("active",sa.Boolean,nullable=False,server_default=sa.true()),sa.Column("created_at",sa.DateTime,nullable=False))
    op.create_index("ix_authorities_active","authorities",["active"]); op.create_index("ix_authorities_jurisdiction","authorities",["jurisdiction"])
    op.create_table("routing_decisions",sa.Column("id",sa.Integer,primary_key=True),sa.Column("incident_id",sa.Integer,sa.ForeignKey("incidents.id"),nullable=False,unique=True),sa.Column("authority_id",sa.Integer,sa.ForeignKey("authorities.id")),sa.Column("jurisdiction",sa.String,nullable=False),sa.Column("source",sa.String,nullable=False),sa.Column("reason",sa.Text,nullable=False),sa.Column("confidence",sa.String,nullable=False),sa.Column("manual_review_required",sa.Boolean,nullable=False),sa.Column("created_at",sa.DateTime,nullable=False))
    op.create_index("ix_routing_decisions_authority_id", "routing_decisions", ["authority_id"])
    op.create_index("ix_routing_decisions_manual_review_required", "routing_decisions", ["manual_review_required"])
    for name in ("incident_assignments","operator_notes","incident_status_history"):
        if name=="incident_assignments": op.create_table(name,sa.Column("id",sa.Integer,primary_key=True),sa.Column("incident_id",sa.Integer,sa.ForeignKey("incidents.id"),nullable=False,unique=True),sa.Column("assigned_to",sa.String,nullable=False),sa.Column("assigned_by",sa.String,nullable=False),sa.Column("created_at",sa.DateTime,nullable=False))
        elif name=="operator_notes": op.create_table(name,sa.Column("id",sa.Integer,primary_key=True),sa.Column("incident_id",sa.Integer,sa.ForeignKey("incidents.id"),nullable=False),sa.Column("author",sa.String,nullable=False),sa.Column("content",sa.Text,nullable=False),sa.Column("created_at",sa.DateTime,nullable=False))
        else: op.create_table(name,sa.Column("id",sa.Integer,primary_key=True),sa.Column("incident_id",sa.Integer,sa.ForeignKey("incidents.id"),nullable=False),sa.Column("previous_status",status,nullable=False),sa.Column("new_status",status,nullable=False),sa.Column("actor",sa.String,nullable=False),sa.Column("source",sa.String,nullable=False),sa.Column("created_at",sa.DateTime,nullable=False))
    op.create_index("ix_incident_assignments_incident_id", "incident_assignments", ["incident_id"])
    op.create_index("ix_operator_notes_incident_id", "operator_notes", ["incident_id"])
    op.create_index("ix_incident_status_history_incident_id", "incident_status_history", ["incident_id"])
    op.create_index("ix_incident_status_history_new_status", "incident_status_history", ["new_status"])
    # Demo configuration only: these are internal routing targets, never API
    # integrations or claims that a complaint was lodged with an authority.
    authorities = sa.table("authorities", sa.column("name", sa.String), sa.column("authority_type", authority_type), sa.column("jurisdiction", sa.String), sa.column("routing_key", sa.String), sa.column("official_channel", sa.String), sa.column("active", sa.Boolean), sa.column("created_at", sa.DateTime))
    op.bulk_insert(authorities, [
        {"name": "Greater Chennai Corporation", "authority_type": "public_local", "jurisdiction": "Chennai", "routing_key": None, "official_channel": None, "active": True, "created_at": datetime.utcnow()},
        {"name": "Tamil Nadu Highways", "authority_type": "public_state", "jurisdiction": "Tamil Nadu", "routing_key": None, "official_channel": None, "active": True, "created_at": datetime.utcnow()},
        {"name": "National Highways Authority of India", "authority_type": "national_highway", "jurisdiction": "India", "routing_key": "NH", "official_channel": None, "active": True, "created_at": datetime.utcnow()},
        {"name": "Campus Facilities", "authority_type": "campus_private", "jurisdiction": "Configured campus", "routing_key": None, "official_channel": None, "active": True, "created_at": datetime.utcnow()},
        {"name": "Manual Review", "authority_type": "unknown", "jurisdiction": "unknown", "routing_key": None, "official_channel": None, "active": True, "created_at": datetime.utcnow()},
    ])
def downgrade():
    op.drop_index("ix_incident_status_history_new_status", table_name="incident_status_history")
    op.drop_index("ix_incident_status_history_incident_id", table_name="incident_status_history")
    op.drop_index("ix_operator_notes_incident_id", table_name="operator_notes")
    op.drop_index("ix_incident_assignments_incident_id", table_name="incident_assignments")
    op.drop_index("ix_routing_decisions_manual_review_required", table_name="routing_decisions")
    op.drop_index("ix_routing_decisions_authority_id", table_name="routing_decisions")
    for table in ("incident_status_history","operator_notes","incident_assignments","routing_decisions","authorities"): op.drop_table(table)
    sa.Enum(name="authoritytype").drop(op.get_bind(), checkfirst=True)
