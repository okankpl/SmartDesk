from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.models.ticket import Ticket, TicketStatus
from app.models.user import User, UserRole

# Erlaubte Ziel-Status pro Ausgangsstatus, jeweils mit den Rollen, die GENAU DIESEN
# Uebergang ausloesen duerfen. Ein Status, der hier fuer einen Ausgangsstatus nicht
# als Schluessel auftaucht, ist von dort aus schlicht nicht erreichbar (z.B. OPEN
# direkt zu CLOSED - kein Ueberspringen der Pipeline).
#
# Herleitung der Regeln (siehe docs/architektur-und-konzepte.md, Abschnitt 5 und 6):
# - OPEN -> IN_PROGRESS: ein Agent (oder Admin) "claimt" das Ticket, faengt an
# - IN_PROGRESS -> RESOLVED: Agent/Admin markiert als geloest
# - RESOLVED -> CLOSED: NUR Admin darf final schliessen (FA-8)
# - RESOLVED -> IN_PROGRESS: der Melder lehnt die Loesung ab und das Ticket geht
#   zurueck in Bearbeitung (oder ein Admin greift korrigierend ein)
# - CLOSED: Endzustand, keine Uebergaenge mehr raus
#
# Ein einfaches verschachteltes dict[Status, dict[Status, set[Rolle]]] reicht bei
# 4 Status/3 Rollen komplett aus - eine State-Machine-Bibliothek waere hier
# unnoetige Komplexitaet (YAGNI, siehe Architektur-Doku).
ALLOWED_TRANSITIONS: dict[TicketStatus, dict[TicketStatus, set[UserRole]]] = {
    TicketStatus.OPEN: {
        TicketStatus.IN_PROGRESS: {UserRole.AGENT, UserRole.ADMIN},
    },
    TicketStatus.IN_PROGRESS: {
        TicketStatus.RESOLVED: {UserRole.AGENT, UserRole.ADMIN},
    },
    TicketStatus.RESOLVED: {
        TicketStatus.CLOSED: {UserRole.ADMIN},
        TicketStatus.IN_PROGRESS: {UserRole.EMPLOYEE, UserRole.ADMIN},
    },
    TicketStatus.CLOSED: {},
}


def apply_status_transition(ticket: Ticket, new_status: TicketStatus, current_user: User) -> None:
    """Prueft einen Statuswechsel gegen ALLOWED_TRANSITIONS und vollzieht ihn.

    Veraendert `ticket` nur, wenn (a) der Uebergang fachlich ueberhaupt existiert
    und (b) die Rolle von `current_user` dafuer freigegeben ist. Sonst wird eine
    passende HTTPException geworfen - der Router muss sich um Fehlerfaelle nicht
    mehr kuemmern, nur noch db.commit() aufrufen, wenn diese Funktion durchlaeuft.
    """
    allowed_roles = ALLOWED_TRANSITIONS.get(ticket.status, {}).get(new_status)
    if allowed_roles is None:
        # 409 statt 400: die Anfrage selbst ist syntaktisch gueltig (new_status ist
        # ein echter TicketStatus-Wert), widerspricht aber dem aktuellen Zustand
        # des Tickets - dieselbe Statuscode-Logik wie beim "Email bereits
        # registriert"-Fall in auth.py.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Übergang von '{ticket.status.value}' zu '{new_status.value}' ist nicht erlaubt",
        )

    if current_user.role not in allowed_roles:
        # 403 statt 401: current_user IST authentifiziert (sonst waeren wir nie
        # hier), hat aber nicht die noetige Rolle - siehe Glossar-Eintrag
        # "Authentifizierung vs. Autorisierung" in den Lernnotizen.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Für diesen Statuswechsel fehlt dir die Berechtigung",
        )

    # Zusaetzliche Pruefung auf OBJEKT-Ebene, nicht nur auf Rollen-Ebene: ein
    # EMPLOYEE darf laut ALLOWED_TRANSITIONS zwar RESOLVED->IN_PROGRESS ausloesen
    # (ablehnen), aber nur bei einem Ticket, das er/sie selbst gemeldet hat - nicht
    # bei fremden Tickets. "Darf diese ROLLE das ueberhaupt" (oben) ist etwas
    # anderes als "darf DIESER Nutzer das bei GENAU DIESEM Ticket" (hier).
    if current_user.role == UserRole.EMPLOYEE and current_user.id != ticket.requester_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nur der Melder eines Tickets darf es ablehnen",
        )

    ticket.status = new_status
    now = datetime.now(timezone.utc)
    if new_status == TicketStatus.RESOLVED:
        ticket.resolved_at = now
    elif new_status == TicketStatus.CLOSED:
        ticket.closed_at = now
