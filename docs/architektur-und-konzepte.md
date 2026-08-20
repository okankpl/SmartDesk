# SmartDesk – Architektur & Konzepte

Diese Datei erklärt **warum** SmartDesk so gebaut ist, wie es gebaut ist, und die wichtigsten technischen Konzepte dahinter. Richtet sich an dich als Anfänger mit ein bisschen Programmiererfahrung (kein völliges Neuland, aber Backend/Docker/Auth sind neu) – als Nachschlagewerk, wenn du später nochmal nachlesen willst, warum eine Entscheidung so gefallen ist.

Die normale [README.md](../README.md) beschreibt nur *wie man das Projekt startet*. Hier geht's um das *Warum* – Spezifikation, Architekturentscheidungen und die Softwaretechnik-Prinzipien dahinter.

**Inhalt:**
1. [Der große Überblick](#1-der-große-überblick)
2. [Spezifikation: was SmartDesk leisten soll](#2-spezifikation-was-smartdesk-leisten-soll)
3. [Tech-Stack: was und warum](#3-tech-stack-was-und-warum)
4. [Aufbau des Backends: die vier Schichten](#4-aufbau-des-backends-die-vier-schichten)
5. [Wichtige Datenmodell-Entscheidungen](#5-wichtige-datenmodell-entscheidungen)
6. [Sicherheitsentscheidungen bei den Auth-Endpunkten](#6-sicherheitsentscheidungen-bei-den-auth-endpunkten)
7. [Softwaretechnik-Prinzipien & Clean Code in SmartDesk](#7-softwaretechnik-prinzipien--clean-code-in-smartdesk)
8. [Frontend-Architekturentscheidungen](#8-frontend-architekturentscheidungen)
9. [Bewusste Einschränkungen & offene Punkte](#9-bewusste-einschränkungen--offene-punkte)
10. [Was noch fehlt (Kurz-Roadmap)](#10-was-noch-fehlt-kurz-roadmap)

---

## 1. Der große Überblick

SmartDesk besteht aus zwei komplett getrennten Programmen, die über HTTP miteinander reden:

- **Frontend** (`frontend/`) – eine Angular-Anwendung, läuft im Browser, zeigt die Oberfläche
- **Backend** (`backend/`) – eine FastAPI-Anwendung (Python), läuft als eigener Server, verwaltet Daten und Geschäftslogik

Diese Trennung nennt man **Client-Server-Architektur**. Warum nicht alles in einem? Weil so beide Teile unabhängig voneinander entwickelt, getestet und sogar auf unterschiedlichen Rechnern betrieben werden können – und weil es dem entspricht, wie echte Firmen-Software heute gebaut wird.

Aktuell sind Frontend und Backend noch **nicht verbunden** – das Frontend zeigt noch Testdaten. Das Verbinden kommt in einer späteren Phase (siehe [Roadmap](#10-was-noch-fehlt-kurz-roadmap)).

---

## 2. Spezifikation: was SmartDesk leisten soll

Dieser Abschnitt ist bewusst getrennt von "Tech-Stack" gehalten – das ist ein Kernprinzip aus der Requirements-Engineering-Lehre: **Spezifikation beschreibt WAS ein System tun soll, unabhängig davon, WIE (mit welcher Technologie) es das tut.** Architekturentscheidungen (Abschnitt 3–8) sind die Antwort auf diese Anforderungen, nicht umgekehrt.

### 2.1 Ausgangslage / Problem

In vielen Unternehmen läuft die interne IT-Unterstützung informell (Zuruf, E-Mail, Chat). Das hat drei typische Probleme, die SmartDesk adressiert:
- **Keine Nachvollziehbarkeit** – niemand kann später sagen, wer ein Problem wann gemeldet und wer es bearbeitet hat.
- **Kein Status** – der Melder weiß nicht, ob "dran gearbeitet wird" oder das Problem vergessen wurde.
- **Keine Priorisierung** – ein kritischer Systemausfall geht in derselben Mail-Inbox unter wie "Drucker klemmt".

SmartDesk löst das mit einem klassischen **ITSM-Ansatz** (IT Service Management – ein etablierter Fachbegriff, z.B. aus ITIL): Anfragen werden als **Tickets** mit festem Lebenszyklus erfasst, statt informell zu verpuffen.

### 2.2 Akteure (Rollen)

In der Requirements Engineering nennt man die "Nutzergruppen von außen" **Akteure (Actors)**. SmartDesk hat drei:

| Akteur | Bedeutung | Code-Entsprechung |
|---|---|---|
| **Employee** | meldet ein Problem (Melder eines Tickets) | `UserRole.EMPLOYEE` |
| **Agent** | bearbeitet gemeldete Tickets | `UserRole.AGENT` |
| **Admin** | verwaltet Nutzer, entscheidet über finale Statuswechsel | `UserRole.ADMIN` |

### 2.3 Funktionale Anforderungen

Funktionale Anforderungen beschreiben **konkretes Verhalten** des Systems ("das System muss X können"). Status zeigt, was schon umgesetzt ist:

| # | Anforderung | Status |
|---|---|---|
| FA-1 | Ein Employee kann sich registrieren (Name, E-Mail, Passwort) | ✅ `POST /auth/register` |
| FA-2 | Ein registrierter Nutzer kann sich einloggen und erhält einen Zugangs-Token | ✅ `POST /auth/login` |
| FA-3 | Ein Nutzer kann ein Ticket mit Titel, Beschreibung und Priorität erstellen | ✅ `POST /tickets` |
| FA-4 | Tickets können gelesen, teilweise aktualisiert und gelöscht werden | ✅ `GET/PATCH/DELETE /tickets/{id}` |
| FA-5 | Ein Ticket durchläuft einen festen Status-Lebenszyklus (offen → in Bearbeitung → gelöst → geschlossen) | 🔶 Datenmodell steht, Übergangsregeln offen (Phase 4) |
| FA-6 | Nur eingeloggte Nutzer dürfen auf Ticket-Endpunkte zugreifen | ✅ `get_current_user`-Dependency (`app/core/deps.py`), an jedem Ticket-Endpunkt |
| FA-7 | Ein Agent kann sich ein Ticket zuweisen bzw. zugewiesen bekommen | 🔶 Datenfeld (`assignee_id`) existiert, kein eigener Endpunkt |
| FA-8 | Nur ein Admin darf ein Ticket final schließen | ⏳ offen (Teil der Lebenszyklus-Regeln) |
| FA-9 | Das Dashboard zeigt Kennzahlen (offene Tickets, kritische Incidents, heute gelöst) | 🔶 UI steht, nutzt noch Mock-Daten statt echter API |

Diese Tabelle selbst ist übrigens ein kleines Beispiel für Requirements-Tracing: jede Zeile lässt sich auf einen Commit oder eine Datei zurückführen – das ist genau das Prinzip, das professionelle RE-Werkzeuge (z.B. Jira, Azure DevOps mit verlinkten Work Items) automatisieren.

### 2.4 Nicht-funktionale Anforderungen

Nicht-funktionale Anforderungen (NFA) beschreiben **Qualitätseigenschaften** statt konkretem Verhalten – oft nach der ISO-25010-Norm kategorisiert:

| Kategorie | Anforderung | Wie SmartDesk das umsetzt |
|---|---|---|
| **Sicherheit** | Passwörter dürfen niemals im Klartext gespeichert werden | bcrypt-Hashing ([Abschnitt 6](#6-sicherheitsentscheidungen-bei-den-auth-endpunkten)) |
| **Sicherheit** | Zugriff muss nachweisbar an einen Nutzer gebunden sein | JWT mit `sub`/`role`/`exp` |
| **Wartbarkeit** | Code muss von anderen Entwicklern verstanden und erweitert werden können | Schichtenarchitektur ([Abschnitt 4](#4-aufbau-des-backends-die-vier-schichten)), durchgängige Kommentare |
| **Nachvollziehbarkeit** | Datenbank-Änderungen müssen versioniert und rückgängig machbar sein | Alembic-Migrationen |
| **Testbarkeit** | Kernlogik muss automatisiert geprüft werden können, ohne die ganze App zu starten | reine Funktionen in `security.py` + pytest + CI |
| **Portabilität** | Die Entwicklungsumgebung muss auf jedem Rechner identisch reproduzierbar sein | Docker Compose |
| **Konsistenz** | Ungültige Datenzustände (z.B. Ticket ohne existierenden Melder) dürfen nicht in der DB landen | Foreign Keys, DB-Enums, serverseitige Prüfungen |

### 2.5 Zwei Anwendungsfälle (Use Cases) im klassischen Format

Ein Use Case beschreibt einen einzelnen, abgeschlossenen Ablauf aus Sicht eines Akteurs – ein Format, das dir in RE-Vorlesungen sehr wahrscheinlich in genau dieser Struktur begegnet (Akteur / Vorbedingung / Ablauf / Nachbedingung / Fehlerfälle):

**UC-1: Ticket erstellen**
- **Akteur:** Employee
- **Vorbedingung:** Nutzer ist registriert (aktuell noch: Nutzer existiert in der DB)
- **Ablauf:** Nutzer sendet `POST /tickets` mit Titel, optionaler Beschreibung, Priorität und `requester_id`
- **Nachbedingung:** Neues Ticket existiert mit Status `open`, ist über `GET /tickets/{id}` abrufbar
- **Fehlerfall:** `requester_id` verweist auf keinen existierenden Nutzer → `404 Not Found` (statt eines rohen Datenbankfehlers, siehe `tickets.py`)

**UC-2: Login**
- **Akteur:** registrierter Nutzer (jede Rolle)
- **Vorbedingung:** Account existiert (`POST /auth/register` wurde vorher erfolgreich aufgerufen)
- **Ablauf:** Nutzer sendet E-Mail + Passwort an `POST /auth/login`
- **Nachbedingung:** Nutzer erhält einen signierten JWT, gültig 60 Minuten
- **Fehlerfall:** E-Mail unbekannt ODER Passwort falsch → in **beiden** Fällen identischer `401 Unauthorized` (bewusste Anti-User-Enumeration-Entscheidung, siehe Abschnitt 6)

### 2.6 Einordnung: Spezifikation vs. Architekturbeschreibung

Kurz zur Begriffsklärung, falls das in deinem Kurs unterschiedlich sauber getrennt wird:
- **Spezifikation / Lastenheft** = *was* soll das System können (Abschnitt 2 hier)
- **Architekturbeschreibung** = *wie* wird das technisch umgesetzt, mit welchen Bausteinen, in welchen Schichten, mit welchen Entscheidungen und Begründungen (Abschnitt 3–8 hier)

Diese Datei mischt beides bewusst in einem Dokument, weil das Projekt dafür klein genug ist – bei größeren Projekten trennt man das oft in eigene Dokumente (z.B. ein Lastenheft/Pflichtenheft getrennt von einer arc42-Architekturdokumentation). Falls dir "arc42" im Kurs begegnet: das ist ein verbreitetes Standard-Gliederungsschema für genau solche Architekturdokumente – vieles hier (Bausteinsicht = Abschnitt 4, Entscheidungen/Rationale = die "Warum"-Boxen überall) folgt lose diesem Gedanken, ohne die volle arc42-Struktur zu übernehmen.

---

## 3. Tech-Stack: was und warum

| Baustein | Wahl | Warum |
|---|---|---|
| Frontend-Framework | Angular | war Ausgangspunkt des Projekts, moderne Signals-API |
| Backend-Framework | FastAPI (Python) | s.u. |
| Datenbank | PostgreSQL | s.u. |
| ORM | SQLAlchemy | s.u. |
| Migrationen | Alembic | s.u. |
| Auth | JWT + bcrypt | s.u. |
| Dev-Umgebung | Docker Compose | s.u. |

### Warum FastAPI?

FastAPI ist ein Python-Framework zum Bauen von REST-APIs. Vorteile, die für dieses Projekt den Ausschlag gaben:
- **Automatische Validierung** – du beschreibst Datenstrukturen einmal (die Pydantic-Schemas in `app/schemas/`), FastAPI prüft jede eingehende Anfrage automatisch dagegen.
- **Automatische Dokumentation** – die Swagger-UI unter `/docs` entsteht komplett automatisch aus deinem Code, ohne dass du sie separat pflegen musst.
- **Type Hints als echtes Werkzeug, nicht nur Deko** – FastAPI liest deine Python-Typannotationen (`def foo(x: int)`) und nutzt sie aktiv für Validierung und Dokumentation.
- Sehr verbreitet in echten Firmen aktuell, gutes Lernsignal fürs Portfolio.

### Warum PostgreSQL?

PostgreSQL ist eine **relationale** Datenbank – Daten liegen in Tabellen mit fest definierten Spalten, Tabellen können über **Fremdschlüssel** (Foreign Keys) miteinander verbunden werden (bei uns: ein Ticket "gehört" über `requester_id` zu einem User). Der Vorteil gegenüber einer dokumentbasierten DB (wie MongoDB oder Firebase Firestore, falls dir das was sagt): die Datenbank selbst erzwingt Konsistenz – ein Ticket kann z.B. gar nicht erst mit einer `requester_id` gespeichert werden, die auf keinen existierenden User zeigt. Das haben wir in Phase 2 direkt genutzt und getestet.

### Warum ein ORM (SQLAlchemy)?

Ein **ORM** (Object-Relational Mapper) übersetzt zwischen "Python-Objekten" und "Datenbank-Tabellenzeilen". Statt rohes SQL zu schreiben (`SELECT * FROM tickets WHERE ...`), schreibst du Python-Code (`db.execute(select(Ticket))`) und SQLAlchemy übersetzt das im Hintergrund in SQL. Vorteil: weniger tippfehler-anfälliger String-SQL-Code, Autovervollständigung, und du bleibst in einer Sprache (Python) statt ständig zwischen Python und SQL zu wechseln.

### Warum Migrationen (Alembic)?

Ein Datenbank-Schema (welche Tabellen, welche Spalten gibt es) verändert sich über die Zeit – bei uns z.B. von "nur Tickets" zu "Tickets + Users mit Fremdschlüsseln". Eine **Migration** ist eine versionierte, nachvollziehbare Beschreibung so einer Änderung (ähnlich wie ein Git-Commit, nur für die Datenbankstruktur statt für Code). Alembic verwaltet diese Migrationen als Python-Dateien in `backend/alembic/versions/`. Der große Vorteil: man kann eine Migration **rückgängig machen** (`downgrade`) und **nachvollziehen**, wer wann was am Schema geändert hat – bei uns in Phase 1 und 2 sogar mit echten Bugs, die wir beim Testen gefunden und gefixt haben (siehe die Kommentare in den Migrationsdateien selbst).

### Warum Docker/Docker Compose?

Docker sorgt dafür, dass Backend und Datenbank **isoliert und reproduzierbar** laufen, ohne dass du Python/PostgreSQL manuell auf Windows installieren musst. `docker compose up` startet beides mit einem Befehl. Ein **Image** ist dabei der unveränderliche Bauplan (Code + Abhängigkeiten + Mini-Betriebssystem-Basis), ein **Container** eine laufende Instanz davon.

### Warum JWT + bcrypt für Auth?

- **bcrypt** hasht Passwörter absichtlich langsam, damit gestohlene Passwort-Hashes nicht in Sekunden durch Ausprobieren geknackt werden können.
- **JWT** merkt sich "wer eingeloggt ist", ohne dass der Server sich selbst was merken muss – skaliert besser und ist der heute übliche Standard für APIs. Details dazu in [Abschnitt 6](#6-sicherheitsentscheidungen-bei-den-auth-endpunkten).

---

## 4. Aufbau des Backends: die vier Schichten

Jede Ressource (z.B. Ticket) ist auf vier Dateien/Schichten aufgeteilt, die jede eine klare Aufgabe hat:

```
Router (app/routers/)      → nimmt HTTP-Anfragen entgegen, ruft die anderen Schichten auf
Schema (app/schemas/)      → beschreibt, wie Ein-/Ausgabe-JSON aussehen darf (Validierung)
Model (app/models/)        → beschreibt die Datenbank-Tabelle (SQLAlchemy)
Service (app/services/)    → Geschäftslogik, die mehr ist als simples Lesen/Schreiben (kommt in Phase 4)
```

Warum diese Trennung? Jede Schicht hat genau eine Verantwortung – der Router weiß nichts über SQL, das Model weiß nichts über HTTP. Das macht jede Schicht einzeln verständlich und testbar, auch wenn das Projekt wächst.

Der Fachbegriff dafür ist **Schichtenarchitektur (Layered Architecture)** – eines der ältesten und am weitesten verbreiteten Architekturmuster überhaupt (dir evtl. auch als "3-Tier-Architektur" o.ä. begegnet). Wenn dich im Studium nach einem *benannten* Architekturmuster für SmartDesk gefragt wird: das hier ist die Antwort, und dieser Abschnitt ist im arc42-Sinn im Grunde die "Bausteinsicht" davon.

---

## 5. Wichtige Datenmodell-Entscheidungen

**Warum drei Rollen (`employee`/`agent`/`admin`) statt z.B. nur "Nutzer"?** Weil ein echtes ITSM-Tool (wie Jira Service Management) genau diese Trennung braucht: Melder ≠ Bearbeiter ≠ Administrator. Das macht die spätere Berechtigungslogik (wer darf ein Ticket schließen?) überhaupt erst sinnvoll.

**Warum 4 Ticket-Status statt 3 (`open`/`in_progress`/`resolved`/`closed`)?** Mit nur 3 Status ist "schließen" eine einzelne Aktion ohne Kontrolle. Mit `resolved` als Zwischenschritt gibt es eine echte Freigabe-Regel: ein Agent markiert als gelöst, aber nur ein Admin (oder der Melder durch Ablehnen) entscheidet über den nächsten Schritt.

**Warum die Status-Übergänge als einfaches Python-Dictionary statt einer State-Machine-Bibliothek?** Bei nur 4 Zuständen ist eine Bibliothek unnötige Komplexität – ein `dict[Status, set[Status]]` ist genauso mächtig, aber ohne zusätzliche Abhängigkeit komplett durchschaubar (kommt in Phase 4). Das ist ein bewusstes **YAGNI**-Prinzip ("You Aren't Gonna Need It") – nicht jede Modellierungsfrage braucht die "enterprise" Lösung.

**Warum `requester_id` und `assignee_id` als zwei getrennte Felder?** Weil "wer hat's gemeldet" und "wer bearbeitet's gerade" unterschiedliche Dinge sind, die sich unabhängig voneinander ändern (ein Ticket kann den Bearbeiter wechseln, der Melder bleibt immer gleich).

---

## 6. Sicherheitsentscheidungen bei den Auth-Endpunkten

`POST /auth/register` und `POST /auth/login` (in `backend/app/routers/auth.py`) enthalten mehrere Design-Entscheidungen, die nicht offensichtlich sind, wenn man nur den Code liest:

**Warum bekommt `RegisterRequest` kein `role`-Feld?** Würde der Client die Rolle selbst mitschicken dürfen, könnte sich jeder bei der Registrierung einfach `role: "admin"` setzen. Die Rolle wird deshalb serverseitig fest auf `EMPLOYEE` gesetzt – der Client hat darauf keinen Einfluss. (Wie ein Nutzer später zu `agent`/`admin` wird, ist bewusst noch offen – das wäre ein eigener, geschützter Endpunkt, den nur ein Admin aufrufen darf, kommt später.)

**Warum `409 Conflict` bei doppelter Email, aber `401 Unauthorized` bei falschem Login?** HTTP-Statuscodes haben feste Bedeutungen: 409 heißt "die Anfrage selbst ist okay, aber sie widerspricht dem aktuellen Zustand der Ressource" (die Email existiert schon). 401 heißt "du bist nicht authentifiziert" – passt für falsche Zugangsdaten. Beide Fälle bewusst unterschiedliche Codes, weil sie fachlich unterschiedliche Dinge bedeuten (Verwendung falscher Statuscodes ist ein klassischer API-Design-Fehler).

**Warum liefern "falsches Passwort" und "Email existiert nicht beim Login" exakt dieselbe Fehlermeldung?** Das ist eine bewusste Sicherheitsentscheidung gegen **User Enumeration**: Würde der Server bei einer unbekannten Email eine andere Meldung zeigen als bei einem falschen Passwort, könnte ein Angreifer systematisch durchprobieren, welche Email-Adressen überhaupt registriert sind – ein Datenschutzproblem für sich, selbst ohne dass ein Passwort geknackt wird.

**Warum `OAuth2PasswordRequestForm` (Formular-Daten) statt JSON beim Login?** Das ist FastAPIs eingebauter, standardisierter Weg für Login-Endpunkte – dadurch funktioniert der "Authorize"-Button in der automatisch generierten Swagger-UI (`/docs`) ohne Zusatzaufwand.

**Was bewusst noch NICHT geprüft wird:** `RegisterRequest.email` ist aktuell ein einfacher `str` (kein Format-Check wie "enthält @"), und `RegisterRequest.password` hat keine Mindestlänge. Das ist keine Nachlässigkeit, sondern ein dokumentierter offener Punkt – siehe [Abschnitt 9](#9-bewusste-einschränkungen--offene-punkte) für die konkrete Lösung, die dafür ansteht.

### Wie die Ticket-Endpunkte jetzt abgesichert sind

`app/core/deps.py` enthält `get_current_user`, eine Dependency, die vor jedem Ticket-Endpunkt läuft (`Depends(get_current_user)` in `tickets.py`):

1. `OAuth2PasswordBearer` liest den Token aus dem `Authorization: Bearer <token>`-Header.
2. `decode_access_token` (aus `security.py`) prüft Signatur und Ablaufzeit – schlägt das fehl (`jwt.PyJWTError`), gibt es sofort `401`.
3. Die `sub`-Claim aus dem Token wird als User-ID benutzt, um den `User` zu laden – existiert er nicht mehr (z.B. gelöscht), ebenfalls `401`.

**Wichtige Unterscheidung:** Das ist **Authentifizierung** ("bist du überhaupt eingeloggt?"), noch keine **Autorisierung** ("darfst du als `employee` wirklich *jedes* Ticket löschen?"). Jeder eingeloggte Nutzer – unabhängig von seiner Rolle – kann aktuell weiterhin alle Ticket-Endpunkte nutzen. Rollenbasierte Einschränkungen (z.B. nur `admin` darf schließen) sind der nächste, noch offene Schritt (siehe [Abschnitt 9](#9-bewusste-einschränkungen--offene-punkte)).

Eine zweite Konsequenz derselben Änderung: `POST /tickets` nimmt `requester_id` nicht mehr vom Client entgegen (das wäre seit es einen eingeloggten Nutzer gibt ein Sicherheitsloch – jeder hätte Tickets im Namen anderer anlegen können), sondern setzt es serverseitig aus `current_user.id`.

---

## 7. Softwaretechnik-Prinzipien & Clean Code in SmartDesk

Dieser Abschnitt macht explizit, welche im Berufsleben verbreiteten Prinzipien in SmartDesk stecken – nützlich, um im Gespräch auf "warum hast du das so gemacht" mit dem korrekten Fachbegriff antworten zu können statt nur "das fand ich sinnvoll".

**Single Responsibility Principle (SRP)** – Teil der SOLID-Prinzipien: jede Einheit (Datei, Klasse, Funktion) sollte genau einen Grund haben, sich zu ändern. Sichtbar an der [Schichtenarchitektur](#4-aufbau-des-backends-die-vier-schichten): ändert sich die Validierungsregel für ein Ticket, ändert sich nur `schemas/ticket.py` – nicht der Router, nicht das Model. Genauso bei `security.py`: die Datei weiß nur etwas über Hashing/JWT, nichts über HTTP oder die Datenbank.

**DRY (Don't Repeat Yourself)** – Wissen soll an genau einer Stelle im Code stehen. Beispiele in SmartDesk:
- `get_settings()` mit `@lru_cache` (`config.py`) – Umgebungsvariablen werden genau einmal eingelesen, nicht bei jedem Zugriff neu.
- `STATUS_LABELS` (`ticket-card.ts`) – die deutschen Beschriftungen für Ticket-Status stehen an einer Stelle, nicht verstreut in jedem Template.
- `viewTabs` (`dashboard.ts`) – eine einzige Datenquelle für Tab-Beschriftung, Filterlogik und Abschnittsüberschrift gleichzeitig, statt das dreimal separat zu pflegen.

**Dependency Injection** – ein Muster, bei dem eine Funktion ihre Abhängigkeiten (z.B. eine Datenbank-Session) von außen gereicht bekommt, statt sie selbst zu beschaffen. Bei uns: `db: Session = Depends(get_db)` in jedem Router. Macht Code testbar: `list_tickets(db: Session = Depends(get_db))` lässt sich in einem Test mit einer Test-Session aufrufen, ohne die echte Datenbank-Verbindungslogik nachbauen zu müssen.

**Fail Fast / frühzeitige Validierung** – Beispiel `create_ticket` in `tickets.py`: statt eine ungültige `requester_id` bis zum `db.commit()` durchlaufen zu lassen (wo sie als kryptischer Postgres-Fehler auffliegen würde), wird sie sofort geprüft und mit einer verständlichen `404`-Antwort abgebrochen. Fehler so früh wie möglich, so verständlich wie möglich melden.

**Testbarkeit als Designkriterium, nicht Nachgedanke** – dass `hash_password`/`verify_password`/`create_access_token` reine Funktionen ohne Datenbank- oder HTTP-Abhängigkeit sind, ist kein Zufall: genau das macht sie in `test_security.py` ohne Testdatenbank, ohne laufenden Server, in Millisekunden testbar.

**Aussagekräftige Namen statt Kommentar-Krücken** – z.B. `openTicketCount`, `verify_password`, `TicketUpdate` statt generischer Namen wie `data` oder `helper`. Guter Name = weniger Erklärungsbedarf.

**Konsistente Commit-Historie (Conventional Commits)** – wirf einen Blick in `git log`: `feat: ...`, `fix: ...`, `docs: ...`, `test: ...`, `ci: ...`, `refactor: ...`. Das ist die verbreitete **Conventional-Commits**-Konvention – jeder Commit sagt in einem Wort, *welche Art* von Änderung er enthält. In echten Teams ermöglicht das automatisch generierte Changelogs und macht `git log` beim Debuggen deutlich lesbarer, statt "fix stuff", "update", "asdf".

**YAGNI ("You Aren't Gonna Need It")** – bewusster Verzicht auf Komplexität, die (noch) nicht gebraucht wird. Siehe die State-Machine-Entscheidung in [Abschnitt 5](#5-wichtige-datenmodell-entscheidungen): kein Framework für 4 Zustände.

---

## 8. Frontend-Architekturentscheidungen

**Smart/Container- vs. Dumb/Presentational-Komponenten** – ein sehr verbreitetes Frontend-Muster (nicht Angular-spezifisch, genauso in React/Vue üblich): eine "Smart"-Komponente hält Zustand und Logik, eine "Dumb"-Komponente bekommt fertige Daten nur gereicht und zeigt sie an, ohne selbst zu wissen, woher sie kommen. SmartDesk setzt das bereits um:
- `Dashboard` (`dashboard.ts`) ist die **Smart Component**: hält `tickets` als Signal, berechnet `openTicketCount`, `visibleTickets` etc.
- `TicketCard` (`ticket-card.ts`) ist **Presentational**: bekommt ein einzelnes `Ticket` über `input.required<Ticket>()` rein, berechnet daraus nur eine Anzeige-Beschriftung (`statusLabel`) – sie weiß nichts über die Gesamtliste, Filter oder Tabs.

Der Vorteil: `TicketCard` lässt sich isoliert wiederverwenden und testen, ohne dass man die ganze Dashboard-Logik mitschleppen muss.

**Signals statt manueller Zustandsverwaltung** – Angular bietet mit RxJS auch einen mächtigeren, aber komplexeren Ansatz für asynchrone Datenströme. Für simplen, synchronen UI-Zustand (welcher Tab ist aktiv, welche Tickets gibt es gerade) sind Signals die schlankere, seit neueren Angular-Versionen empfohlene Lösung – wieder ein Fall von "die einfachste Lösung wählen, die das Problem tatsächlich löst", nicht das mächtigste verfügbare Werkzeug.

**Neue `@for`/`@empty`-Control-Flow-Syntax** statt des älteren `*ngFor` – seit Angular 17 die empfohlene, kompiler-geprüfte Syntax für Schleifen/bedingte Anzeige in Templates (sichtbar in `dashboard.html`), u.a. mit eingebautem `@empty`-Block für den Leerzustand ("Keine Tickets in dieser Ansicht.").

**Barrierefreiheit (Accessibility) von Anfang an mitgedacht** – `aria-label`, `role="tablist"`/`role="tab"`, `aria-selected` sind bereits im Code (`dashboard.html`, `main-layout.html`). Das ist keine nachträgliche Fleißaufgabe, sondern ein Qualitätsmerkmal, das in echten Frontend-Jobs regelmäßig explizit gefordert wird (Stichwort WCAG).

---

## 9. Bewusste Einschränkungen & offene Punkte

Ehrlich zu benennen, was fehlt, ist selbst ein Qualitätsmerkmal. Hier die aktuell bekannten Lücken, mit der jeweils "richtigen" Lösung:

| Lücke | Warum sie (noch) offen ist | Wie man sie in echt schließt |
|---|---|---|
| Keine Rollenprüfung (Autorisierung) auf Endpunkt-Ebene | Authentifizierung (`get_current_user`) steht seit Phase 4a, Rollenprüfung ist der direkt darauf aufbauende nächste Schritt | z.B. `require_role(UserRole.ADMIN)` als weitere Dependency, bevor ein Ticket final geschlossen werden darf |
| `RegisterRequest.email` prüft kein E-Mail-Format | Bewusst zurückgestellt, um Register/Login zuerst end-to-end zum Laufen zu bringen | Pydantics `EmailStr`-Typ statt `str` (braucht das zusätzliche Package `email-validator` in `requirements.txt`) |
| `RegisterRequest.password` hat keine Mindestlänge/-stärke | s.o. | ein `Field(min_length=8)` oder ein eigener Pydantic-`validator` |
| Kein Logout / kein Token-Widerruf | JWTs sind zustandslos per Design (siehe Abschnitt 3) – "Widerruf" widerspricht dem Grundprinzip | entweder kurze Ablaufzeiten + Refresh-Token-Flow, oder eine serverseitige Blockliste für widerrufene Tokens |
| `GET /tickets`, `GET /users` liefern immer die komplette Liste | Für die aktuelle, kleine Testdatenmenge unkritisch | Pagination (`?limit=20&offset=0`), Standard bei jeder wachsenden REST-API |
| CORS erlaubt fest nur `localhost:4200` | Passt für lokale Entwicklung | in Produktion über eine Umgebungsvariable konfigurierbar machen, nicht hart codieren |
| Frontend zeigt noch Mock-Daten, ist nicht an die API angebunden | Backend mit Auth ist gerade erst fertig geworden | `HttpClient`-Service im Frontend, der `tickets`-Signal aus einem echten `GET /tickets`-Aufruf befüllt |
| Keine Integrationstests (nur Unit-Tests für `security.py`) | Erster Testfokus lag bewusst auf der isoliertesten, am einfachsten testbaren Logik | FastAPIs `TestClient` + eine Test-Datenbank (z.B. SQLite in-memory oder ein Test-Postgres-Container in der CI) |

---

## 10. Was noch fehlt (Kurz-Roadmap)

1. ~~`/auth/register`, `/auth/login`-Endpunkte~~ – erledigt
2. ~~Ticket-Endpunkte gegen den JWT absichern (Authentifizierung)~~ – erledigt, `get_current_user`-Dependency
3. Rollenbasierte Autorisierung + Ticket-Lifecycle-Regeln (wer darf welchen Status-Übergang machen)
4. Frontend an die echte API anbinden (Mock-Daten raus)
5. Kommentare/Zusatzfunktionen
6. Weitere Tests (Ticket-Endpunkte, Auth-Endpunkte), CI um eine Test-Datenbank erweitern
7. Politur, Deployment-Feinschliff

Ausführlicher Phasenplan: siehe die Commit-Historie (`git log`) – jeder Phasen-Commit beschreibt, was dazukam und warum.
