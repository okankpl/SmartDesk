# SmartDesk

SmartDesk ist ein IT-Ticket-Management-System: Mitarbeitende erfassen Support-Anfragen als Tickets, Support-Mitarbeitende bearbeiten sie über einen Status-Lebenszyklus (offen → in Bearbeitung → gelöst → geschlossen).

Warum welche Technologie gewählt wurde, wichtige Konzepte (Docker, Hashing, JWT, ...) und alle Architekturentscheidungen ausführlich erklärt: siehe [docs/architektur-und-konzepte.md](docs/architektur-und-konzepte.md).

## Struktur

- `frontend/` – Angular-Anwendung (Standalone Components, Signals)
- `backend/` – FastAPI-Anwendung (REST-API, PostgreSQL über SQLAlchemy + Alembic)

## Aktueller Stand

- **Ticket-CRUD** – `GET/POST/PATCH/DELETE /tickets`, mit Prioritäts- und Status-Enums, Fremdschlüsseln zu `User`
- **User-Modell** – Rollen `employee`/`agent`/`admin`, noch keine Registrierung/Login-Endpunkte
- **Auth-Bausteine fertig, aber noch nicht verdrahtet** – Passwort-Hashing (bcrypt) und JWT-Erzeugung/-Prüfung (`backend/app/core/security.py`) sind fertig und getestet, aber es gibt noch keine `/auth/register`/`/auth/login`-Endpunkte, die sie benutzen
- **Frontend und Backend sind noch nicht verbunden** – das Dashboard zeigt weiterhin Mock-Daten

Nächste Schritte: Auth-Endpunkte, dann Ticket-Lifecycle-Regeln, dann Frontend-Anbindung.

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
