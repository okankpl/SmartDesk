"""Gemeinsame Anfrage-Budgets fuer den Login: abgelehnte Anfragen erreichen
weder bcrypt noch die Datenbank (siehe Architektur-Doku, "Login-Drosselung")."""

from functools import lru_cache
import hashlib
import hmac
import math
import time

from fastapi import HTTPException, status
from limits import RateLimitItemPerSecond
from limits.errors import StorageError
from limits.storage import Storage, storage_from_string
from limits.strategies import MovingWindowRateLimiter

from app.core.config import Settings, get_settings


class LoginRateLimiter:
    def __init__(self, settings: Settings, storage: Storage):
        self.storage = storage
        self.limiter = MovingWindowRateLimiter(storage)
        self.secret = settings.secret_key.encode("utf-8")
        self.budgets = (
            ("ip", RateLimitItemPerSecond(settings.login_rate_limit_ip_attempts, settings.login_rate_limit_ip_window_seconds)),
            ("account", RateLimitItemPerSecond(settings.login_rate_limit_account_attempts, settings.login_rate_limit_account_window_seconds)),
        )

    def identifier(self, scope: str, value: str) -> str:
        # Keine E-Mail-Adressen oder IPs im Klartext in Redis-Schluesseln (und damit
        # auch nicht in der AOF-Protokolldatei von Redis): HMAC mit dem SECRET_KEY
        # ergibt pro Wert einen festen, aber nicht zurueckrechenbaren Schluessel.
        payload = f"smartdesk-login-v1\0{scope}\0{value}".encode("utf-8")
        return hmac.new(self.secret, payload, hashlib.sha256).hexdigest()

    def enforce(self, email: str, client_ip: str) -> None:
        values = {"ip": client_ip, "account": email.strip().lower()}
        try:
            for scope, budget in self.budgets:
                key = self.identifier(scope, values[scope])
                if not self.limiter.hit(budget, scope, key):
                    window = self.limiter.get_window_stats(budget, scope, key)
                    retry_after = max(1, math.ceil(window.reset_time - time.time()))
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Zu viele Anmeldeversuche. Bitte später erneut versuchen.",
                        headers={"Retry-After": str(retry_after), "Cache-Control": "no-store"},
                    )
        except StorageError as exc:
            raise self.unavailable() from exc

    def check_storage(self) -> bool:
        try:
            return self.storage.check()
        except StorageError:
            return False

    @staticmethod
    def unavailable() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Anmeldung derzeit nicht verfügbar. Bitte später erneut versuchen.",
            headers={"Retry-After": "30", "Cache-Control": "no-store"},
        )


@lru_cache
def get_login_rate_limiter() -> LoginRateLimiter:
    settings = get_settings()
    storage = storage_from_string(
        settings.login_rate_limit_storage_uri,
        key_prefix="smartdesk:login:v1",
        wrap_exceptions=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    return LoginRateLimiter(settings, storage)
