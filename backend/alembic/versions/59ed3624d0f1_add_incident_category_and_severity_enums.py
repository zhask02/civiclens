"""add incident category and severity enums

Revision ID: 59ed3624d0f1
Revises:
Create Date: 2026-08-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "59ed3624d0f1"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This is the base revision.  It must create the original table before
    # later revisions can convert its string fields to PostgreSQL enums.
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("severity", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    category_enum = sa.Enum(
        "pothole",
        "streetlight",
        "garbage",
        "drainage",
        "road_damage",
        "water_leak",
        "other",
        name="incidentcategory",
    )

    severity_enum = sa.Enum(
        "low",
        "medium",
        "high",
        "critical",
        name="incidentseverity",
    )

    category_enum.create(op.get_bind(), checkfirst=True)
    severity_enum.create(op.get_bind(), checkfirst=True)

    op.execute(
        """
        ALTER TABLE incidents
        ALTER COLUMN category TYPE incidentcategory
        USING category::text::incidentcategory
        """
    )

    op.execute(
        """
        ALTER TABLE incidents
        ALTER COLUMN severity TYPE incidentseverity
        USING severity::text::incidentseverity
        """
    )


def downgrade() -> None:
    op.alter_column(
        "incidents",
        "severity",
        type_=sa.VARCHAR(length=50),
        existing_nullable=True,
        postgresql_using="severity::text",
    )

    op.alter_column(
        "incidents",
        "category",
        type_=sa.VARCHAR(length=100),
        existing_nullable=True,
        postgresql_using="category::text",
    )

    severity_enum = sa.Enum(
        "low",
        "medium",
        "high",
        "critical",
        name="incidentseverity",
    )

    category_enum = sa.Enum(
        "pothole",
        "streetlight",
        "garbage",
        "drainage",
        "road_damage",
        "water_leak",
        "other",
        name="incidentcategory",
    )

    severity_enum.drop(op.get_bind(), checkfirst=True)
    category_enum.drop(op.get_bind(), checkfirst=True)
    op.drop_table("incidents")
