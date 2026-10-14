from sqlalchemy import DateTime

from app.core.database import Base

# Wie in alembic/env.py: erst durch den Import landen die Tabellen in
# Base.metadata - sonst haette der Test unten nichts zu pruefen.
from app.models.comment import Comment  # noqa: F401
from app.models.ticket import Ticket  # noqa: F401
from app.models.user import User  # noqa: F401


def test_every_datetime_column_stores_its_time_zone():
    """Ohne Zeitzone in der Spalte lieferte die API Uhrzeiten wie
    "14:07:59" ohne Zusatz, der Browser las sie als deutsche Ortszeit und
    zeigte sie 1-2 Stunden zu frueh an. Der Test laeuft ueber ALLE Tabellen,
    damit auch eine spaeter hinzugefuegte Datumsspalte auffaellt, falls sie die
    Regel aus Base.type_annotation_map (core/database.py) umgeht - etwa durch
    ein explizites mapped_column(DateTime, ...)."""
    datetime_columns = [
        column
        for table in Base.metadata.tables.values()
        for column in table.columns
        if isinstance(column.type, DateTime)
    ]
    columns_without_time_zone = [
        f"{column.table.name}.{column.name}" for column in datetime_columns if not column.type.timezone
    ]

    # Erst sicherstellen, dass ueberhaupt Spalten gefunden wurden - sonst
    # waere die zweite Pruefung auch bei einem kaputten Import "gruen".
    assert len(datetime_columns) >= 7
    assert columns_without_time_zone == []
