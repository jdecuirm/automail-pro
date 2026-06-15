"""add demo user seed data

Revision ID: 0aa9a4979722
Revises: efa204059f21
Create Date: 2026-06-15 12:27:03.585402

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0aa9a4979722"
down_revision: Union[str, Sequence[str], None] = "efa204059f21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Insert demo user used by the temporary auth stub (Stage D)."""
    op.execute(
        """
        INSERT INTO users (id, email, is_active, created_at, updated_at)
        VALUES (
            '00000000-0000-0000-0000-000000000001',
            'demo@automail.local',
            true,
            now(),
            now()
        )
        ON CONFLICT (id) DO NOTHING
        """
    )


def downgrade() -> None:
    """Remove the demo user seed row."""
    op.execute(
        """
        DELETE FROM users
        WHERE id = '00000000-0000-0000-0000-000000000001'
        """
    )
