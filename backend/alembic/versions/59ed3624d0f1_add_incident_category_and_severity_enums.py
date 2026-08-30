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