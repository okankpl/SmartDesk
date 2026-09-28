"""cascade delete comments with ticket

Revision ID: c3f1a9e5d742
Revises: 08da48c27cd7
Create Date: 2026-09-28 11:30:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'c3f1a9e5d742'
down_revision = '08da48c27cd7'
branch_labels = None
depends_on = None

# Name, den PostgreSQL dem Fremdschluessel in 08da48c27cd7 automatisch gegeben
# hat (Schema "<tabelle>_<spalte>_fkey") - die Migration dort hat keinen
# eigenen Namen vergeben. "alembic revision --autogenerate" erkennt die
# Aenderung zwar, kann einen unbenannten Constraint aber nicht gezielt loeschen
# und warnt entsprechend - deshalb steht der Name hier ausdruecklich.
FK_NAME = 'comments_ticket_id_fkey'


def upgrade() -> None:
    # Ein bestehender Fremdschluessel laesst sich in PostgreSQL nicht einfach
    # "umstellen" - er wird geloescht und mit ON DELETE CASCADE neu angelegt.
    # Beides passiert in derselben Transaktion (Alembic auf PostgreSQL), es
    # gibt also keinen Moment, in dem die Tabelle ohne Pruefung dasteht.
    op.drop_constraint(FK_NAME, 'comments', type_='foreignkey')
    op.create_foreign_key(FK_NAME, 'comments', 'tickets', ['ticket_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    op.drop_constraint(FK_NAME, 'comments', type_='foreignkey')
    op.create_foreign_key(FK_NAME, 'comments', 'tickets', ['ticket_id'], ['id'])
