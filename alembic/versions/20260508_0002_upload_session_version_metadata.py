"""Add target metadata to upload sessions.

Revision ID: 20260508_0002
Revises: 20260508_0001
Create Date: 2026-05-08
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260508_0002"
down_revision: str | None = "20260508_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "upload_sessions",
        sa.Column(
            "target_version_number",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "upload_sessions",
        sa.Column(
            "target_content_type",
            sa.String(length=255),
            nullable=False,
            server_default="application/octet-stream",
        ),
    )
    op.add_column(
        "upload_sessions",
        sa.Column("target_size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "upload_sessions",
        sa.Column("target_checksum_sha256", sa.String(length=64), nullable=True),
    )
    op.alter_column("upload_sessions", "target_version_number", server_default=None)
    op.alter_column("upload_sessions", "target_content_type", server_default=None)
    op.alter_column("upload_sessions", "target_size_bytes", server_default=None)


def downgrade() -> None:
    op.drop_column("upload_sessions", "target_checksum_sha256")
    op.drop_column("upload_sessions", "target_size_bytes")
    op.drop_column("upload_sessions", "target_content_type")
    op.drop_column("upload_sessions", "target_version_number")
