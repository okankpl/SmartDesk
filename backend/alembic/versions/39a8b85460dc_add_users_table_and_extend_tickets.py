"""add users table and extend tickets

Revision ID: 39a8b85460dc
Revises: eb4f534443bf
Create Date: 2026-08-19 13:42:36.448661

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '39a8b85460dc'
down_revision = 'eb4f534443bf'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users-Tabelle ---
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=200), nullable=False),
        sa.Column('role', sa.Enum('employee', 'agent', 'admin', name='user_role'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # Seed-User: Platzhalter-Passwort, wird nie fuers echte Einloggen benutzt.
    # Existiert nur, damit alte Tickets (ohne echten Melder) unten ein gueltiges
    # requester_id bekommen koennen. Phase 3 ersetzt Registrierung durch echtes Hashing.
    op.execute(
        """
        INSERT INTO users (email, hashed_password, full_name, role)
        VALUES ('seed@smartdesk.local', 'not-a-real-hash', 'Seed User', 'employee')
        """
    )

    # --- tickets: einfache neue Spalten (alle nullable, brauchen kein Backfill) ---
    op.add_column('tickets', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('tickets', sa.Column('resolved_at', sa.DateTime(), nullable=True))
    op.add_column('tickets', sa.Column('closed_at', sa.DateTime(), nullable=True))

    # --- tickets: requester_id, NICHT-NULL, aber mit Backfill fuer Bestandsdaten ---
    # Reihenfolge ist hier entscheidend, sonst schlaegt die Migration an bestehenden
    # Zeilen fehl: 1) Spalte erst NULLABLE anlegen, 2) bestehende Zeilen befuellen
    # (Backfill), 3) ERST DANACH die NOT-NULL-Regel scharf schalten.
    op.add_column('tickets', sa.Column('requester_id', sa.Integer(), nullable=True))
    op.execute(
        "UPDATE tickets SET requester_id = "
        "(SELECT id FROM users WHERE email = 'seed@smartdesk.local') "
        "WHERE requester_id IS NULL"
    )
    op.alter_column('tickets', 'requester_id', nullable=False)
    op.create_foreign_key('tickets_requester_id_fkey', 'tickets', 'users', ['requester_id'], ['id'])

    # assignee_id bleibt nullable ("noch niemand zugewiesen") - kein Backfill noetig.
    op.add_column('tickets', sa.Column('assignee_id', sa.Integer(), nullable=True))
    op.create_foreign_key('tickets_assignee_id_fkey', 'tickets', 'users', ['assignee_id'], ['id'])

    # --- tickets: priority von Integer zu Enum ---
    # Ein Integer laesst sich nicht eindeutig automatisch einem Enum-Wert zuordnen
    # (ist "3" medium oder high? reine Businessentscheidung). Statt einer riskanten
    # impliziten Typumwandlung: Spalte ersetzen, alle bestehenden Zeilen bekommen den
    # neutralen Default "medium". Fuer Testdaten hier vertretbar - bei echten
    # Produktionsdaten waere stattdessen eine explizite Mapping-Tabelle noetig.
    op.drop_column('tickets', 'priority')
    priority_enum = sa.Enum('low', 'medium', 'high', 'critical', name='ticket_priority')
    priority_enum.create(op.get_bind())
    op.add_column(
        'tickets',
        sa.Column('priority', priority_enum, nullable=False, server_default='medium'),
    )

    # --- tickets: status-Enum um 'resolved' erweitern ---
    # Autogenerate erkennt Aenderungen an bestehenden ENUM-Werten nicht automatisch -
    # das muss man von Hand ergaenzen. IF NOT EXISTS macht die Migration wiederholbar.
    op.execute("ALTER TYPE ticket_status ADD VALUE IF NOT EXISTS 'resolved'")


def downgrade() -> None:
    op.drop_constraint('tickets_assignee_id_fkey', 'tickets', type_='foreignkey')
    op.drop_constraint('tickets_requester_id_fkey', 'tickets', type_='foreignkey')

    op.drop_column('tickets', 'priority')
    sa.Enum(name='ticket_priority').drop(op.get_bind(), checkfirst=True)
    op.add_column('tickets', sa.Column('priority', sa.Integer(), nullable=False, server_default='1'))

    op.drop_column('tickets', 'assignee_id')
    op.drop_column('tickets', 'requester_id')
    op.drop_column('tickets', 'closed_at')
    op.drop_column('tickets', 'resolved_at')
    op.drop_column('tickets', 'description')

    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    # Gleicher Fall wie beim ticket_priority-Enum oben: drop_table() entfernt den
    # zugehoerigen Postgres-ENUM-Typ nicht automatisch.
    sa.Enum(name='user_role').drop(op.get_bind(), checkfirst=True)

    # Hinweis: Postgres kann einzelne Werte nicht wieder aus einem ENUM-Typ entfernen,
    # ohne ihn komplett neu zu erstellen - 'resolved' bleibt im Typ ticket_status auch
    # nach einem Downgrade bestehen. Fuer dieses Projekt unkritisch, daher bewusst
    # nicht geloest (kein Produktivbetrieb mit strikten Downgrade-Anforderungen).
