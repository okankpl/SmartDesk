from fastapi import Response

from app.core.config import get_settings
from app.core.security import ACCESS_TOKEN_COOKIE_NAME


def set_session_cookie(response: Response, token: str, max_age_seconds: int) -> None:
    """Legt den JWT als Sitzungs-Cookie in die Antwort.

    Die EINE Stelle fuer die sicherheitsrelevanten Cookie-Flags - genutzt vom
    normalen Login (routers/auth.py) und vom Start bzw. Rollenwechsel der
    oeffentlichen Demo (routers/demo.py). Zwei Kopien dieser Flags koennten
    sonst unbemerkt auseinanderlaufen (z.B. secure nur an einer Stelle).
    """
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=token,
        max_age=max_age_seconds,
        httponly=True,  # per JavaScript nicht lesbar - schuetzt vor Token-Diebstahl per XSS
        samesite="lax",  # wird nicht bei Cross-Site-Requests von anderen Domains mitgeschickt (CSRF-Schutz)
        # secure=True wuerde den Cookie nur ueber HTTPS uebertragen. Aus
        # get_settings().cookie_secure statt hartcodiert: lokal (http://)
        # per Default False, in Produktion per Umgebungsvariable auf True
        # umstellbar (siehe docs/deployment.md).
        secure=get_settings().cookie_secure,
        path="/",
    )
    # Antworten, die eine Sitzung ausgeben, darf kein Cache zwischenspeichern.
    response.headers["Cache-Control"] = "no-store"
