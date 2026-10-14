"""store timestamps with time zone

Revision ID: 50d4c94502eb
Revises: c3f1a9e5d742
Create Date: 2026-10-14 16:30:00.000000

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '50d4c94502eb'
down_revision = 'c3f1a9e5d742'
branch_labels = None
depends_on = None

# Alle Datumsspalten, die bisher "timestamp WITHOUT time zone" waren (siehe
# type_annotation_map in app/core/database.py, warum sich das aendert).
# Paare aus (Tabelle, Spalte).
TIMESTAMP_COLUMNS = [
    ('users', 'created_at'),
    ('users', 'updated_at'),
    ('tickets', 'created_at'),
    ('tickets', 'updated_at'),
    ('tickets', 'resolved_at'),
    ('tickets', 'closed_at'),
    ('comments', 'created_at'),
]


def upgrade() -> None:
    for table, column in TIMESTAMP_COLUMNS:
        # postgresql_using haengt "USING <ausdruck>" an das ALTER COLUMN an:
        # so rechnet PostgreSQL jeden BESTEHENDEN Wert beim Umstellen des Typs
        # um. "AT TIME ZONE 'UTC'" heisst: die bisher gespeicherte Uhrzeit ohne
        # Zeitzone war UTC (das offizielle postgres-Image laeuft standardmaessig
        # mit der Zeitzone UTC, now() hat also UTC-Uhrzeiten geschrieben). Ohne
        # diese Angabe wuerde PostgreSQL stattdessen die Zeitzone der aktuellen
        # Verbindung annehmen - auf einem anders eingestellten Server waeren
        # alle alten Zeitstempel danach still um einige Stunden verschoben.
        # existing_type beschreibt den bisherigen Typ, nur fuer Alembics
        # eigene Buchfuehrung (z.B. fuer die Ausgabe von "upgrade --sql").
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=True),
            existing_type=sa.DateTime(),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    for table, column in TIMESTAMP_COLUMNS:
        # Rueckweg: aus dem eindeutigen Zeitpunkt wieder eine reine UTC-Uhrzeit
        # machen - dieselbe Annahme wie vor dieser Migration.
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(),
            existing_type=sa.DateTime(timezone=True),
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
