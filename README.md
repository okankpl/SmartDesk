# SmartDesk

SmartDesk ist ein IT-Ticket-Management-System: Mitarbeitende erfassen Support-Anfragen als Tickets, Support-Mitarbeitende bearbeiten sie über einen Status-Lebenszyklus (offen → in Bearbeitung → gelöst → geschlossen).

Warum welche Technologie gewählt wurde, wichtige Konzepte (Docker, Hashing, JWT, ...) und alle Architekturentscheidungen ausführlich erklärt: siehe [docs/architektur-und-konzepte.md](docs/architektur-und-konzepte.md).

## Struktur

- `frontend/` – Angular-Anwendung (Standalone Components, Signals)
- `backend/` – FastAPI-Anwendung (REST-API, PostgreSQL über SQLAlchemy + Alembic)

## Aktueller Stand

- **Ticket-CRUD** – `GET/POST/PATCH/DELETE /tickets`, mit Prioritäts- und Status-Enums, Fremdschlüsseln zu `User`
- **Auth** – `POST /auth/register`, `POST /auth/login` (JWT via bcrypt-Passwort-Hashing), getestet
- **Ticket-Endpunkte sind geschützt** – `/tickets` verlangt einen gültigen JWT (`Authorization: Bearer <token>`)
- **Ticket-Lifecycle mit Rollenregeln** – `PATCH /tickets/{id}/status` prüft Status-Übergänge gegen Rollen (z.B. nur `admin` darf final schließen), getestet
- **Rollenbasierte Autorisierung auf allen Ticket-Endpunkten** – `employee` sieht nur eigene Tickets, `PATCH`/`DELETE` sind `agent`/`admin` vorbehalten, getestet
- **Login-Flow steht** – Frontend loggt sich gegen das echte Backend ein, Session per HttpOnly-Cookie (kein Token im Frontend-JS lesbar), Route-Guard schützt das Dashboard
- **Dashboard zeigt echte Daten** – Kennzahlen und die vier Status-Ansichten kommen live aus `GET /tickets`, nicht mehr aus Mock-Daten
- **Ticket erstellen, Details ansehen & Status ändern über die Oberfläche** – `/tickets/new`, anklickbare Ticket-Karten öffnen ein Detail-Popup mit Beschreibung und passenden Aktions-Buttons (Claim/Lösen/Schließen/Ablehnen) – welche Buttons erscheinen, berechnet das Backend pro Rolle/Status, nicht das Frontend
- **Frontend-Komponenten-/Service-Tests** – `Auth`, `authGuard`, `TicketCard`, `Dashboard`, mit gemocktem `HttpClient`, eigene CI-Pipeline
- **Deployment vorbereitet** – produktionsfähige Konfiguration (konfigurierbare CORS-Origin/Cookie-Flags, Angular-Environments), VPS-Anleitung samt Betriebs-Skripten (`scripts/`)

Nächste Schritte: Registrierungs-Seite im Frontend, echte HTTP-Integrationstests im Backend, VPS-Deployment tatsächlich durchführen.

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

Läuft danach unter http://localhost:4200. Es gibt noch keine Registrierungs-Seite im Frontend – einen Test-Account vorher über die Swagger UI anlegen (`POST /auth/register` unter http://localhost:8000/docs), dann damit auf http://localhost:4200/login einloggen.

## Tests ausführen

```bash
# Backend (im backend-Container)
docker compose exec backend pytest -v

# Frontend
cd frontend
npm test
```

Beide laufen automatisch bei jedem Push/PR auf `main` über GitHub Actions (`.github/workflows/backend-tests.yml`, `.github/workflows/frontend-tests.yml`).

## Datenbank-Migrationen (Alembic)

Migrationen laufen im `backend`-Container:

```bash
docker compose exec backend alembic revision --autogenerate -m "beschreibung"
docker compose exec backend alembic upgrade head
```

## Deployment

Anleitung für ein Deployment auf einem eigenen VPS (Docker, Caddy mit automatischem HTTPS): siehe [docs/deployment.md](docs/deployment.md).
