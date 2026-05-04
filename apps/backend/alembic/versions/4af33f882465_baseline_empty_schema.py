"""baseline_empty_schema

Revision ID: 4af33f882465
Revises:
Create Date: 2026-05-04 09:09:47.312511

Empty baseline: establishes Alembic version tracking before first DDL migration.
"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "4af33f882465"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
