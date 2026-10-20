"""add private demo workspaces

Revision ID: ccca87eb18e9
Revises: b42e8f19a620
Create Date: 2026-10-19 17:00:00.000000

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = 'ccca87eb18e9'
down_revision = 'b42e8f19a620'
branch_labels = None
depends_on = None

# Tabellen, deren Zeilen zu einem Demo-Arbeitsbereich gehoeren koennen.
# Kommentare und Historie brauchen keine eigene Spalte: sie haengen immer an
# einem Ticket und werden mit ihm geloescht (bestehendes ON DELETE CASCADE).
WORKSPACE_TABLES = ('users', 'tickets')


def upgrade() -> None:
    op.create_table(
        'demo_workspaces',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_demo_workspaces_expires_at', 'demo_workspaces', ['expires_at'])

    for table in WORKSPACE_TABLES:
        # nullable: alle bestehenden Konten und Tickets sind normale Daten
        # ausserhalb der oeffentlichen Demo und behalten workspace_id = NULL.
        op.add_column(table, sa.Column('workspace_id', sa.Integer(), nullable=True))
        # Eigener, fester Constraint-Name (statt des von PostgreSQL vergebenen),
        # damit downgrade() ihn gezielt loeschen kann - siehe die gleiche
        # Ueberlegung in c3f1a9e5d742.
        op.create_foreign_key(
            f'{table}_workspace_id_fkey', table, 'demo_workspaces',
            ['workspace_id'], ['id'], ondelete='CASCADE',
        )
        op.create_index(f'ix_{table}_workspace_id', table, ['workspace_id'])


def downgrade() -> None:
    for table in reversed(WORKSPACE_TABLES):
        op.drop_index(f'ix_{table}_workspace_id', table_name=table)
        op.drop_constraint(f'{table}_workspace_id_fkey', table, type_='foreignkey')
        op.drop_column(table, 'workspace_id')
    op.drop_index('ix_demo_workspaces_expires_at', table_name='demo_workspaces')
    op.drop_table('demo_workspaces')
