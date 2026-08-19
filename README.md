# SmartDesk

SmartDesk ist ein IT-Ticket-Management-System: Mitarbeitende erfassen Support-Anfragen als Tickets, Support-Mitarbeitende bearbeiten sie über einen Status-Lebenszyklus (offen → in Bearbeitung → gelöst → geschlossen).

## Struktur

- `frontend/` – Angular-Anwendung (Standalone Components, Signals)
- `backend/` – FastAPI-Anwendung (REST-API, PostgreSQL über SQLAlchemy + Alembic)

## Backend lokal starten

Voraussetzung: [Docker Desktop](https://www.docker.com/products/docker-desktop/) ist installiert und läuft.

```bash
cp .env.example .env   # einmalig, falls noch nicht vorhanden
docker compose up --build
```

Danach:
- API-Dokumentation (Swagger UI): http://localhost:8000/docs
- Health-Check: http://localhost:8000/health

## Frontend lokal starten

```bash
cd frontend
npm install
npm start
```

Läuft danach unter http://localhost:4200.

## Datenbank-Migrationen (Alembic)

Migrationen laufen im `backend`-Container:

```bash
docker compose exec backend alembic revision --autogenerate -m "beschreibung"
docker compose exec backend alembic upgrade head
```
