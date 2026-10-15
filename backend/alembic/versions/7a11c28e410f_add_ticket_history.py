"""Add an application history for ticket changes.

Revision ID: 7a11c28e410f
Revises: 50d4c94502eb
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "7a11c28e410f"
down_revision = "50d4c94502eb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ticket_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("changes", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ticket_events_ticket_id", "ticket_events", ["ticket_id"])


def downgrade() -> None:
    op.drop_table("ticket_events")
