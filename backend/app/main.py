# "from X import Y" holt sich NUR den Namen Y aus dem Modul/Paket X - nicht alles.
# FastAPI ist die Haupt-Klasse des Frameworks, mit der man die App-Instanz erzeugt.
from fastapi import Depends, FastAPI, HTTPException, status

# CORSMiddleware liegt in einem Untermodul (fastapi.middleware.cors), daher der Punkt-Pfad.
from fastapi.middleware.cors import CORSMiddleware

# text(...) verpackt rohes SQL so, dass SQLAlchemy es ausführen darf;
# SQLAlchemyError ist die Basisklasse aller Datenbankfehler von SQLAlchemy.
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.error_handlers import register_error_handlers

# "app.routers" ist unser eigener Ordner backend/app/routers/. "tickets" ist die Datei
# tickets.py darin. Wir importieren das ganze Modul (nicht nur eine Funktion daraus),
# damit wir unten "tickets.router" schreiben können.
from app.routers import auth, comments, ticket_events, tickets, users

# FastAPI(...) ruft den Konstruktor der Klasse auf und erzeugt ein Objekt - "app" IST
# jetzt unsere Anwendung. title="..." ist ein Keyword-Argument (Parameter wird über
# seinen Namen statt seiner Position übergeben), taucht später in der Swagger-UI auf.
app = FastAPI(title="SmartDesk API")

# app.add_middleware(...) registriert Code, der bei JEDER Anfrage automatisch mitläuft,
# bevor sie unsere Endpunkte erreicht. Middleware = "dazwischengeschalteter" Code.
# Ohne CORS würde der Browser Anfragen von localhost:4200 (Angular) zu localhost:8000
# (dieses Backend) blockieren, weil es zwei unterschiedliche Ports/Origins sind.
app.add_middleware(
    CORSMiddleware,
    # Aus get_settings().frontend_origin statt hartcodiert - lokal per Default
    # weiterhin localhost:4200, in Produktion per Umgebungsvariable auf die
    # echte Domain umstellbar (siehe docs/deployment.md). [...] ist eine
    # Python-Liste - CORSMiddleware will eine Liste erlaubter Adressen, auch
    # wenn es bei uns nur genau eine ist.
    allow_origins=[get_settings().frontend_origin],
    # "*" als String ist hier ein Wildcard-Wert von CORSMiddleware, kein Python-Operator -
    # bedeutet "erlaube alle HTTP-Methoden" (GET, POST, PATCH, ...).
    allow_methods=["*"],
    allow_headers=["*"],
    # Ohne das wuerde der Browser den Auth-Cookie NIE mitschicken, egal was das
    # Frontend anfragt - Cookies gelten bei Cross-Origin-Anfragen (4200 -> 8000
    # sind zwei Origins) standardmaessig als sicherheitskritisch und werden nur
    # mitgesendet/angenommen, wenn Server UND Client das explizit erlauben
    # (hier; im Frontend die passende Gegenstelle: withCredentials).
    allow_credentials=True,
)

# Übersetzt fachliche Fehler aus den Services (z.B. "Statuswechsel nicht
# erlaubt") in passende HTTP-Antworten (409, 403, 404) - siehe
# core/error_handlers.py.
register_error_handlers(app)

# Bindet alle Endpunkte, die in tickets.py mit @router.get/@router.post definiert sind,
# in diese App ein. tickets.router ist das APIRouter-Objekt, das dort erzeugt wurde -
# der Punkt "." greift auf ein Attribut/Objekt innerhalb des Moduls zu.
app.include_router(auth.router)
app.include_router(tickets.router)
app.include_router(comments.router)
app.include_router(ticket_events.router)
app.include_router(users.router)


# @app.get("/health") ist ein Decorator (die Zeile mit @ direkt über einer Funktion).
# Ein Decorator "registriert" die folgende Funktion bei FastAPI: "wenn eine GET-Anfrage
# auf /health reinkommt, ruf health() auf und schick das Rückgabe-Objekt als Antwort."
@app.get("/health")
# "-> dict[str, str]" ist der Type Hint für den Rückgabewert: ein Dictionary (vergleichbar
# mit einem JS-Objekt / einer Map), dessen Schlüssel UND Werte beides Strings sind.
def health() -> dict[str, str]:
    # Bewusst ohne DB-Zugriff: prüft nur, ob der Prozess überhaupt läuft und
    # Anfragen annimmt ("Liveness"). Ob er auch arbeiten KANN, prüft
    # /health/ready unten.
    # {"status": "ok"} ist ein Dictionary-Literal. FastAPI wandelt das automatisch in
    # JSON um (kein manuelles json.dumps() nötig).
    return {"status": "ok"}


@app.get("/health/ready")
def readiness(db: Session = Depends(get_db)) -> dict[str, str]:
    """Prüft, ob das Backend wirklich arbeiten kann, also auch die Datenbank
    erreicht ("Readiness") - anders als /health oben, das nur sagt "der
    Prozess läuft".

    Der Unterschied ist für die Überwachung wichtig: mit falschem Datenbank-
    Passwort oder gestopptem Postgres-Container antwortet /health weiter
    "ok", obwohl jede echte Anfrage mit 500 scheitert. scripts/deploy.sh
    und scripts/healthcheck.sh fragen deshalb diesen Endpunkt ab.
    503 Service Unavailable ist der Standard-Statuscode für "gerade nicht
    einsatzbereit, später erneut versuchen".
    """
    try:
        # "SELECT 1" ist die kleinstmögliche Abfrage: sie liest keine Tabelle,
        # beweist aber, dass Verbindung und Anmeldung bei Postgres klappen.
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Datenbank nicht erreichbar")
    return {"status": "ok", "database": "ok"}
