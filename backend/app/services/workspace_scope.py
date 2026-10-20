"""Die Grenze zwischen Demo-Arbeitsbereichen, an EINER Stelle formuliert.

Jede Sichtbarkeitsregel (Tickets in services/ticket_access.py, Personen in
services/user_access.py) verlangt zusaetzlich "gleicher Arbeitsbereich".
Normale Daten ausserhalb der oeffentlichen Demo haben workspace_id = NULL und
bilden damit ihren eigenen Bereich: normale Konten sehen keine Demo-Daten,
Demo-Konten keine normalen Daten und keine fremden Arbeitsbereiche.
"""
from sqlalchemy import ColumnElement


def same_workspace(column: ColumnElement, workspace_id: int | None) -> ColumnElement[bool]:
    """SQL-Bedingung "column gehoert zum Arbeitsbereich workspace_id".

    Die Falle dabei: "workspace_id = NULL" ist in SQL NIE wahr - NULL heisst
    "unbekannt", und unbekannt = unbekannt ergibt wieder unbekannt. Ein
    einfaches column == workspace_id wuerde normalen Konten (workspace_id
    None) deshalb ALLE normalen Daten verstecken. Fuer sie braucht es
    "IS NULL". In Python dagegen ist None == None True - die Regel fuer
    einzelne Objekte (z.B. is_ticket_visible) kann direkt vergleichen.

    Bewusst zwei Formen statt "IS NOT DISTINCT FROM" (das NULL korrekt
    vergleicht): "= 7" und "IS NULL" kann PostgreSQL ueber den Index auf
    workspace_id beantworten, "IS NOT DISTINCT FROM" nicht.
    """
    return column.is_(None) if workspace_id is None else column == workspace_id
