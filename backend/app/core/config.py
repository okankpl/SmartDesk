# functools ist Teil der Python-Standardbibliothek (kein externes Package).
# lru_cache ist ein Decorator, der Funktionsergebnisse zwischenspeichert (Cache).
from functools import lru_cache

# pydantic_settings ist ein externes Package (steht in requirements.txt).
# Aus ihm importieren wir zwei Namen: die Klasse BaseSettings und die Klasse
# SettingsConfigDict. Mehrere Importe aus demselben Modul trennt man mit Komma.
from pydantic_settings import BaseSettings, SettingsConfigDict


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


# @lru_cache direkt über einer Funktion (ohne Klammern dahinter) heißt: "cache das
# Ergebnis dieser Funktion". Beim ersten Aufruf von get_settings() wird Settings()
# einmal erzeugt (liest dabei alle Env-Variablen), bei jedem weiteren Aufruf wird
# einfach das gespeicherte Ergebnis zurückgegeben statt neu zu lesen.
@lru_cache
def get_settings() -> Settings:
    return Settings()
