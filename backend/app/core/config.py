# functools ist Teil der Python-Standardbibliothek (kein externes Package).
# lru_cache ist ein Decorator, der Funktionsergebnisse zwischenspeichert (Cache).
from functools import lru_cache

from pydantic import field_validator

# pydantic_settings ist ein externes Package (steht in requirements.txt).
# Aus ihm importieren wir zwei Namen: die Klasse BaseSettings und die Klasse
# SettingsConfigDict. Mehrere Importe aus demselben Modul trennt man mit Komma.
from pydantic_settings import BaseSettings, SettingsConfigDict

# Der Platzhalter aus .env.example - steht oeffentlich im Git-Repository.
# Wird er versehentlich unveraendert uebernommen, kann JEDER, der das Repo
# kennt, gueltige JWTs fuer beliebige Nutzer (auch Admins) selbst signieren.
SECRET_KEY_PLACEHOLDER = "change-me-to-a-random-value"
# 32 Zeichen = Untergrenze, ab der PyJWT fuer HS256 nicht mehr warnt (RFC 7518
# verlangt einen Schluessel mindestens so lang wie der Hash, also 256 Bit).
# secrets.token_hex(32) erzeugt 64 Zeichen und liegt damit sicher darueber.
SECRET_KEY_MIN_LENGTH = 32


# "class Settings(BaseSettings):" - Settings ERBT von BaseSettings (wie "extends" in TS).
# Dadurch bekommt Settings automatisch die Fähigkeit, sich selbst aus Umgebungsvariablen
# zu befüllen, ohne dass wir das selbst programmieren müssen.
class Settings(BaseSettings):
    """Liest die Anwendungskonfiguration aus Umgebungsvariablen (bzw. einer .env-Datei)."""

    # Ein Klassen-Attribut (keine Funktion). SettingsConfigDict(...) ist ein Aufruf mit
    # zwei Keyword-Argumenten: env_file sagt "lies zusätzlich aus der Datei .env",
    # extra="ignore" sagt "wirf keinen Fehler, wenn in .env noch andere, hier nicht
    # deklarierte Variablen stehen (z.B. POSTGRES_USER)".
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # database_url: str  -  ein Type Hint OHNE Wert dahinter. Das ist bei Pydantic-Klassen
    # eine Feld-Deklaration: "es MUSS eine Umgebungsvariable DATABASE_URL geben, und ihr
    # Wert wird als database_url (automatisch klein geschrieben erkannt) bereitgestellt."
    # Pydantic vergleicht Feldnamen standardmäßig case-insensitive mit Env-Variablen.
    database_url: str
    secret_key: str

    # Zwei production-bezogene Einstellungen mit lokal sinnvollen Defaults
    # (= Wert, der gilt, wenn die Umgebungsvariable NICHT gesetzt ist) - anders
    # als database_url/secret_key oben, die ohne Wert in der Umgebung einen
    # Fehler auslösen. In der lokalen .env muss also nichts geaendert werden,
    # nur auf dem Server (siehe docs/deployment.md).
    #
    # Die Herkunfts-Adresse, die CORS als "darf zugreifen" akzeptiert (siehe
    # main.py). Lokal das Angular-Dev-Serve, in Produktion die echte Domain.
    frontend_origin: str = "http://localhost:4200"
    # Ob der Auth-Cookie nur ueber HTTPS uebertragen werden darf (siehe
    # auth.py). Lokal laeuft alles ueber http://, deshalb False - in
    # Produktion MUSS das True sein, sonst schuetzt HttpOnly allein nicht vor
    # einem Angreifer, der den Netzwerkverkehr mitliest.
    cookie_secure: bool = False

    # "Fail Fast" beim Start: lieber startet das Backend gar nicht (mit
    # klarer Fehlermeldung), als dass es mit einem erratbaren Schluessel
    # laeuft - das faellt sonst niemandem auf, bis jemand Tokens faelscht.
    @field_validator("secret_key")
    @classmethod
    def secret_key_must_be_strong(cls, value: str) -> str:
        if value == SECRET_KEY_PLACEHOLDER or len(value) < SECRET_KEY_MIN_LENGTH:
            raise ValueError(
                f"SECRET_KEY ist der Platzhalter aus .env.example oder kuerzer als "
                f"{SECRET_KEY_MIN_LENGTH} Zeichen. Neuen Wert erzeugen mit: "
                'python -c "import secrets; print(secrets.token_hex(32))"'
            )
        return value


# @lru_cache direkt über einer Funktion (ohne Klammern dahinter) heißt: "cache das
# Ergebnis dieser Funktion". Beim ersten Aufruf von get_settings() wird Settings()
# einmal erzeugt (liest dabei alle Env-Variablen), bei jedem weiteren Aufruf wird
# einfach das gespeicherte Ergebnis zurückgegeben statt neu zu lesen.
@lru_cache
def get_settings() -> Settings:
    return Settings()
