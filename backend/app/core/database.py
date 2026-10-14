# Generator ist ein Typ aus der Standardbibliothek, den man für Funktionen mit "yield"
# als Rückgabetyp angibt (mehr dazu unten bei get_db).
from collections.abc import Generator
from datetime import datetime

# create_engine baut die eigentliche "Verbindung" zur Datenbank auf (genauer: verwaltet
# einen Pool von Verbindungen im Hintergrund). DateTime ist der SQLAlchemy-Spaltentyp
# für Zeitpunkte (siehe type_annotation_map in Base unten).
from sqlalchemy import DateTime, create_engine

# DeclarativeBase, Session und sessionmaker sind drei einzelne Namen aus demselben
# Untermodul sqlalchemy.orm.
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

# Modul-Ebene, kein "def" oder "class" - läuft einmal beim ersten Import dieser Datei.
# get_settings() ruft die im vorherigen File gecachte Funktion auf und liest .database_url
# per Punkt-Zugriff aus dem zurückgegebenen Settings-Objekt aus.
#
# pool_pre_ping=True: bevor der Pool eine gespeicherte Verbindung an einen Request
# herausgibt, prüft SQLAlchemy mit einer winzigen Test-Abfrage, ob sie noch lebt,
# und ersetzt sie sonst still durch eine neue. Ohne das endete nach einem Neustart
# des Postgres-Containers (Update, Absturz, "restart: unless-stopped") die jeweils
# erste Anfrage mit einem 500-Fehler ("terminating connection due to administrator
# command") - der Pool hielt noch die alte, inzwischen getrennte Verbindung.
# Kostet pro Request einen sehr kurzen zusätzlichen Weg zur Datenbank.
engine = create_engine(get_settings().database_url, pool_pre_ping=True)

# sessionmaker(...) ist eine "Fabrik-Funktion": sie gibt uns nicht direkt eine Session,
# sondern etwas, das wir später (SessionLocal()) aufrufen können, um neue Sessions zu
# erzeugen - vergleichbar mit einer Klasse, die man instanziiert.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Eine Klasse, die von DeclarativeBase erbt. Sie dient als gemeinsamer "Marker": jede
# Tabelle in unserer App erbt von genau dieser Base - und damit auch die Regel unten.
class Base(DeclarativeBase):
    """Gemeinsame Basisklasse, von der alle SQLAlchemy-Modelle erben."""

    # type_annotation_map legt fest, welcher Datenbank-Spaltentyp zu welchem
    # Python-Typ in "Mapped[...]" gehört. Ohne diesen Eintrag wird aus
    # Mapped[datetime] eine Spalte "timestamp WITHOUT time zone": PostgreSQL
    # speichert dann nur die Uhrzeit (bei uns in UTC), aber nicht, in welcher
    # Zeitzone sie gilt. Die API lieferte deshalb "2026-10-14T14:07:59" ohne
    # Zeitzonen-Angabe, und der Browser las das als deutsche Ortszeit - jede
    # angezeigte Uhrzeit lag 1-2 Stunden daneben.
    # timezone=True macht daraus "timestamp WITH time zone" (kurz timestamptz):
    # gespeichert wird ein eindeutiger Zeitpunkt, die API liefert ihn mit
    # Zeitzone ("...Z" = UTC), und der Browser rechnet ihn korrekt in die
    # Ortszeit um. Die Regel steht HIER statt an jeder einzelnen Spalte, damit
    # auch jede künftige Datumsspalte automatisch richtig angelegt wird.
    type_annotation_map = {datetime: DateTime(timezone=True)}


# "-> Generator[Session, None, None]" heißt: diese Funktion liefert Werte vom Typ Session
# über "yield" (statt "return"), erwartet aber keine Eingabe- oder Rückgabewerte beim
# Generator selbst (die beiden "None").
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    # try/finally (wie in Java oder TypeScript): der finally-Block läuft
    # IMMER, auch wenn im try-Block ein Fehler auftritt.
    try:
        # yield statt return: die Funktion "pausiert" hier und übergibt "db" nach außen.
        # FastAPI ruft diese Funktion über Depends(get_db) auf, benutzt die Session für
        # die Dauer eines Requests, und sobald der Request fertig ist, läuft der Code
        # HINTER yield (also db.close()) automatisch weiter.
        yield db
    finally:
        db.close()
