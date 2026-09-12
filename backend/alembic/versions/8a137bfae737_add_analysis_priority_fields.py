"""add analysis priority fields

Revision ID: 8a137bfae737
Revises: 26e233acf904
Create Date: 2026-09-11 23:35:55.305114

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# Revision identifiers used by Alembic.
revision: str = "8a137bfae737"
down_revision: Union[str, Sequence[str], None] = "26e233acf904"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add and backfill the new analysis priority fields."""

    # Add the columns as nullable first because existing analysis rows
    # do not have values for these fields yet.
    op.add_column(
        "evidence_analyses",
        sa.Column(
            "severity_score",
            sa.Float(),
            nullable=True,
        ),
    )

    op.add_column(
        "evidence_analyses",
        sa.Column(
            "priority_score",
            sa.Float(),
            nullable=True,
        ),
    )

    # Create the PostgreSQL enum type used by PriorityLevel.
    priority_level_enum = postgresql.ENUM(
        "low",
        "medium",
        "high",
        "critical",
        name="prioritylevel",
    )

    priority_level_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "evidence_analyses",
        sa.Column(
            "priority_level",
            priority_level_enum,
            nullable=True,
        ),
    )

    op.add_column(
        "evidence_analyses",
        sa.Column(
            "requires_review",
            sa.Boolean(),
            nullable=True,
        ),
    )

    # Backfill existing historical analyses.
    #
    # The existing database contains one manually-created HIGH analysis.
    # We give it the corresponding severity base score and use the same
    # value for priority because the old record has no historical
    # location-aware priority calculation.
    op.execute(
        """
        UPDATE evidence_analyses
        SET
            severity_score = CASE severity
                WHEN 'low' THEN 25
                WHEN 'medium' THEN 50
                WHEN 'high' THEN 75
                WHEN 'critical' THEN 100
            END,
            priority_score = CASE severity
                WHEN 'low' THEN 25
                WHEN 'medium' THEN 50
                WHEN 'high' THEN 75
                WHEN 'critical' THEN 100
            END,
            priority_level = severity::text::prioritylevel,
            requires_review = false
        """
    )

    # Now that every existing row has been populated, enforce the
    # non-null constraints required by the application model.
    op.alter_column(
        "evidence_analyses",
        "severity_score",
        existing_type=sa.Float(),
        nullable=False,
    )

    op.alter_column(
        "evidence_analyses",
        "priority_score",
        existing_type=sa.Float(),
        nullable=False,
    )

    op.alter_column(
        "evidence_analyses",
        "priority_level",
        existing_type=priority_level_enum,
        nullable=False,
    )

    op.alter_column(
        "evidence_analyses",
        "requires_review",
        existing_type=sa.Boolean(),
        nullable=False,
    )


def downgrade() -> None:
    """Remove the analysis priority fields."""

    # Drop columns before removing their PostgreSQL enum type.
    op.drop_column(
        "evidence_analyses",
        "requires_review",
    )

    op.drop_column(
        "evidence_analyses",
        "priority_level",
    )

    op.drop_column(
        "evidence_analyses",
        "priority_score",
    )

    op.drop_column(
        "evidence_analyses",
        "severity_score",
    )

    # Remove the PostgreSQL enum created by this migration.
    priority_level_enum = postgresql.ENUM(
        "low",
        "medium",
        "high",
        "critical",
        name="prioritylevel",
    )

    priority_level_enum.drop(op.get_bind(), checkfirst=True)