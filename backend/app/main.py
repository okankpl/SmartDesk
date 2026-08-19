# "from X import Y" holt sich NUR den Namen Y aus dem Modul/Paket X - nicht alles.
# FastAPI ist die Haupt-Klasse des Frameworks, mit der man die App-Instanz erzeugt.
from fastapi import FastAPI

# CORSMiddleware liegt in einem Untermodul (fastapi.middleware.cors), daher der Punkt-Pfad.
from fastapi.middleware.cors import CORSMiddleware

# "app.routers" ist unser eigener Ordner backend/app/routers/. "tickets" ist die Datei
# tickets.py darin. Wir importieren das ganze Modul (nicht nur eine Funktion daraus),
# damit wir unten "tickets.router" schreiben können.
from app.routers import tickets, users

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
    # [...] ist eine Python-Liste. Hier: die einzige erlaubte Herkunfts-Adresse.
    allow_origins=["http://localhost:4200"],
    # "*" als String ist hier ein Wildcard-Wert von CORSMiddleware, kein Python-Operator -
    # bedeutet "erlaube alle HTTP-Methoden" (GET, POST, PATCH, ...).
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bindet alle Endpunkte, die in tickets.py mit @router.get/@router.post definiert sind,
# in diese App ein. tickets.router ist das APIRouter-Objekt, das dort erzeugt wurde -
# der Punkt "." greift auf ein Attribut/Objekt innerhalb des Moduls zu.
app.include_router(tickets.router)
app.include_router(users.router)


# @app.get("/health") ist ein Decorator (die Zeile mit @ direkt über einer Funktion).
# Ein Decorator "registriert" die folgende Funktion bei FastAPI: "wenn eine GET-Anfrage
# auf /health reinkommt, ruf health() auf und schick das Rückgabe-Objekt als Antwort."
@app.get("/health")
# "-> dict[str, str]" ist der Type Hint für den Rückgabewert: ein Dictionary (vergleichbar
# mit einem JS-Objekt / einer Map), dessen Schlüssel UND Werte beides Strings sind.
def health() -> dict[str, str]:
    # Bewusst ohne DB-Zugriff: prüft nur, ob der Container überhaupt läuft.
    # {"status": "ok"} ist ein Dictionary-Literal. FastAPI wandelt das automatisch in
    # JSON um (kein manuelles json.dumps() nötig).
    return {"status": "ok"}
