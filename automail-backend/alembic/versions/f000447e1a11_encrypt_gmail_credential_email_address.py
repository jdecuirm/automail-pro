"""encrypt_gmail_credential_email_address

Revision ID: f000447e1a11
Revises: 0aa9a4979722
Create Date: 2026-06-17 12:58:11.567885

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f000447e1a11"
down_revision: Union[str, Sequence[str], None] = "0aa9a4979722"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Delete any existing rows — they hold plaintext email_address that cannot
    # be retroactively encrypted without FERNET_KEY access inside a migration.
    # In dev this table is always empty (Stage G is first use of gmail_credentials).
    op.execute("DELETE FROM gmail_credentials")

    # Change email_address from VARCHAR(320) to BYTEA
    op.drop_column("gmail_credentials", "email_address")
    op.add_column(
        "gmail_credentials",
        sa.Column("email_address", sa.LargeBinary(), nullable=False),
    )

    # Add needs_reconnect boolean flag
    op.add_column(
        "gmail_credentials",
        sa.Column(
            "needs_reconnect",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("gmail_credentials", "needs_reconnect")
    op.drop_column("gmail_credentials", "email_address")
    op.add_column(
        "gmail_credentials",
        sa.Column("email_address", sa.String(320), nullable=False, server_default=""),
    )
