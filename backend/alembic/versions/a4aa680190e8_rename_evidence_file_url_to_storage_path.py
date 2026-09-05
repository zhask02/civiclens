"""rename evidence file url to storage path

Revision ID: a4aa680190e8
Revises: 6bcc62bdaae6
Create Date: 2026-09-06 01:43:57.165957

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a4aa680190e8'
down_revision: Union[str, Sequence[str], None] = '6bcc62bdaae6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "incident_evidence",
        "file_url",
        new_column_name="storage_path",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "incident_evidence",
        "storage_path",
        new_column_name="file_url",
    )
