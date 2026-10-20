from pydantic import BaseModel

from app.models.user import UserRole


class DemoConfig(BaseModel):
    """Antwort von GET /demo/config: was das Frontend auf der Anmeldeseite
    anbieten soll ("Demo starten" ja/nein, Registrieren ja/nein)."""

    public_demo: bool
    registration_enabled: bool
    workspace_ttl_hours: int


class DemoRoleSwitch(BaseModel):
    """Eingabe fuer POST /demo/sessions/role. Nur die Rolle - WELCHES Konto es
    wird, bestimmt der Server aus dem Arbeitsbereich des angemeldeten Kontos,
    nie der Client (derselbe Gedanke wie beim Mass-Assignment-Schutz)."""

    role: UserRole
