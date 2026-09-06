"""add evidence analysis table

Revision ID: 26e233acf904
Revises: a4aa680190e8
Create Date: 2026-09-06 15:48:43.065328

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "26e233acf904"
down_revision: Union[str, Sequence[str], None] = "a4aa680190e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    category_enum = postgresql.ENUM(
        "pothole",
        "streetlight",
        "garbage",
        "drainage",
        "road_damage",
        "water_leak",
        "other",
        name="incidentcategory",
        create_type=False,
    )

    severity_enum = postgresql.ENUM(
        "low",
        "medium",
        "high",
        "critical",
        name="incidentseverity",
        create_type=False,
    )

    op.create_table(
        "evidence_analyses",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "evidence_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "category",
            category_enum,
            nullable=False,
        ),
        sa.Column(
            "severity",
            severity_enum,
            nullable=False,
        ),
        sa.Column(
            "confidence",
            sa.Float(),
            nullable=False,
        ),
        sa.Column(
            "model_name",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id"],
            ["incident_evidence.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table("evidence_analyses")