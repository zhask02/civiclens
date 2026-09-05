"""add incident status enum

Revision ID: 67b60c917da7
Revises: 59ed3624d0f1
Create Date: 2026-08-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "67b60c917da7"
down_revision: Union[str, Sequence[str], None] = "59ed3624d0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    status_enum = sa.Enum(
        "submitted",
        "analyzed",
        "assigned",
        "in_progress",
        "resolved",
        name="incidentstatus",
    )

    status_enum.create(op.get_bind(), checkfirst=True)

    op.execute(
        """
        ALTER TABLE incidents
        ALTER COLUMN status TYPE incidentstatus
        USING status::text::incidentstatus
        """
    )


def downgrade() -> None:
    op.alter_column(
        "incidents",
        "status",
        type_=sa.VARCHAR(length=50),
        existing_nullable=False,
        postgresql_using="status::text",
    )

    status_enum = sa.Enum(
        "submitted",
        "analyzed",
        "assigned",
        "in_progress",
        "resolved",
        name="incidentstatus",
    )

    status_enum.drop(op.get_bind(), checkfirst=True)