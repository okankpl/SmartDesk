# Generator ist ein Typ aus der Standardbibliothek, den man für Funktionen mit "yield"
# als Rückgabetyp angibt (mehr dazu unten bei get_db).
from collections.abc import Generator

# create_engine baut die eigentliche "Verbindung" zur Datenbank auf (genauer: verwaltet
# einen Pool von Verbindungen im Hintergrund).
from sqlalchemy import create_engine

# DeclarativeBase, Session und sessionmaker sind drei einzelne Namen aus demselben
# Untermodul sqlalchemy.orm.
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

# Modul-Ebene, kein "def" oder "class" - läuft einmal beim ersten Import dieser Datei.
# get_settings() ruft die im vorherigen File gecachte Funktion auf und liest .database_url
# per Punkt-Zugriff aus dem zurückgegebenen Settings-Objekt aus.
engine = create_engine(get_settings().database_url)

# sessionmaker(...) ist eine "Fabrik-Funktion": sie gibt uns nicht direkt eine Session,
# sondern etwas, das wir später (SessionLocal()) aufrufen können, um neue Sessions zu
# erzeugen - vergleichbar mit einer Klasse, die man instanziiert.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Eine leere Klasse, die nur von DeclarativeBase erbt. Sie hat selbst keinen eigenen Code
# (deshalb kein "pass" nötig, der Docstring reicht als Klassenkörper). Sie dient als
# gemeinsamer "Marker": jede Tabelle in unserer App erbt später von genau dieser Base.
class Base(DeclarativeBase):
    """Gemeinsame Basisklasse, von der alle SQLAlchemy-Modelle erben."""


# "-> Generator[Session, None, None]" heißt: diese Funktion liefert Werte vom Typ Session
# über "yield" (statt "return"), erwartet aber keine Eingabe- oder Rückgabewerte beim
# Generator selbst (die beiden "None").
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    # try/finally kennst du vermutlich aus anderen Sprachen: der finally-Block läuft
    # IMMER, auch wenn im try-Block ein Fehler auftritt.
    try:
        # yield statt return: die Funktion "pausiert" hier und übergibt "db" nach außen.
        # FastAPI ruft diese Funktion über Depends(get_db) auf, benutzt die Session für
        # die Dauer eines Requests, und sobald der Request fertig ist, läuft der Code
        # HINTER yield (also db.close()) automatisch weiter.
        yield db
    finally:
        db.close()
