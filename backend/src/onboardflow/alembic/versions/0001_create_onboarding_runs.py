"""create onboarding runs

Revision ID: 0001_create_onboarding_runs
Revises:
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_create_onboarding_runs"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "onboarding_runs",
        sa.Column("run_id", sa.String(length=64), primary_key=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("message", sa.String(length=512), nullable=False),
        sa.Column("input_data", sa.JSON(), nullable=False),
        sa.Column("validation_result", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("markdown", sa.String(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("action_history", sa.JSON(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("onboarding_runs")

