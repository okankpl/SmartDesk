"""add comments table

Revision ID: 08da48c27cd7
Revises: 39a8b85460dc
Create Date: 2026-09-25 11:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '08da48c27cd7'
down_revision = '39a8b85460dc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Von Hand geschrieben statt per "alembic revision --autogenerate" (Docker
    # lief beim Erstellen nicht) - Struktur exakt an models/comment.py
    # ausgerichtet. Keine Backfill-Logik noetig wie in 39a8b85460dc: die
    # Tabelle ist neu, es gibt keine Bestandszeilen, die erst befuellt werden
    # muessten, bevor NOT-NULL-Constraints greifen koennen.
    op.create_table(
        'comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id']),
        sa.ForeignKeyConstraint(['author_id'], ['users.id']),
    )
    op.create_index(op.f('ix_comments_ticket_id'), 'comments', ['ticket_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_comments_ticket_id'), table_name='comments')
    op.drop_table('comments')
