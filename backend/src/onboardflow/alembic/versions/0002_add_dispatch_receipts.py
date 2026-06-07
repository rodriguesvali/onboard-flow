"""add dispatch receipts

Revision ID: 0002_add_dispatch_receipts
Revises: 0001_create_onboarding_runs
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_add_dispatch_receipts"
down_revision = "0001_create_onboarding_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "onboarding_runs",
        sa.Column("dispatch_receipts", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("onboarding_runs", "dispatch_receipts")
