"""Add optimistic version tracking to tickets.

Revision ID: b42e8f19a620
Revises: 7a11c28e410f
"""
from alembic import op
import sqlalchemy as sa

revision = "b42e8f19a620"
down_revision = "7a11c28e410f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))


def downgrade() -> None:
    op.drop_column("tickets", "version")
