"""Begrenzt, wie oft eine IP-Adresse neue Demo-Arbeitsbereiche anlegen darf.

Jeder Klick auf "Demo starten" schreibt drei Konten und rund 60 Zeilen in die
Datenbank. Ohne Grenze koennte ein Skript in kurzer Zeit tausende Bereiche
anlegen. Nutzt denselben Redis-Speicher und dieselbe Moving-Window-Strategie
wie die Login-Drosselung (core/login_rate_limit.py), mit eigenem Zaehler.
"""
from functools import lru_cache
import math
import time

from fastapi import HTTPException, status
from limits import RateLimitItemPerSecond
from limits.errors import StorageError
from limits.storage import Storage
from limits.strategies import MovingWindowRateLimiter

from app.core.config import Settings, get_settings
from app.core.login_rate_limit import get_login_rate_limiter, hashed_identifier

SCOPE = "demo_ip"


class DemoSessionLimiter:
    def __init__(self, settings: Settings, storage: Storage):
        self.limiter = MovingWindowRateLimiter(storage)
        self.secret = settings.secret_key.encode("utf-8")
        self.budget = RateLimitItemPerSecond(
            settings.demo_session_ip_attempts, settings.demo_session_ip_window_seconds,
        )

    def enforce(self, client_ip: str) -> None:
        """Zaehlt einen neuen Arbeitsbereich fuer diese IP; 429 mit Retry-After,
        wenn das Budget erschoepft ist, 503, wenn Redis nicht erreichbar ist -
        wie beim Login gibt es keine unbegrenzte Ausweichloesung."""
        key = hashed_identifier(self.secret, SCOPE, client_ip)
        try:
            if not self.limiter.hit(self.budget, SCOPE, key):
                window = self.limiter.get_window_stats(self.budget, SCOPE, key)
                retry_after = max(1, math.ceil(window.reset_time - time.time()))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Von dieser Adresse wurden gerade viele Demos gestartet. Bitte später erneut versuchen.",
                    headers={"Retry-After": str(retry_after), "Cache-Control": "no-store"},
                )
        except StorageError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Die Demo ist gerade nicht verfügbar. Bitte später erneut versuchen.",
                headers={"Retry-After": "30", "Cache-Control": "no-store"},
            ) from exc


@lru_cache
def get_demo_session_limiter() -> DemoSessionLimiter:
    # Teilt sich die Redis-Verbindung mit der Login-Drosselung, statt eine
    # zweite aufzubauen.
    return DemoSessionLimiter(get_settings(), get_login_rate_limiter().storage)
