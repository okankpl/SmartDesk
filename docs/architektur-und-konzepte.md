# SmartDesk – Architektur & Konzepte

Diese Datei erklärt **warum** SmartDesk so gebaut ist, wie es gebaut ist, und die wichtigsten technischen Konzepte dahinter. Richtet sich an dich als Anfänger mit ein bisschen Programmiererfahrung (kein völliges Neuland, aber Backend/Docker/Auth sind neu) – als Nachschlagewerk, wenn du später nochmal nachlesen willst, warum eine Entscheidung so gefallen ist.

Die normale [README.md](../README.md) beschreibt nur *wie man das Projekt startet*. Hier geht's um das *Warum*.

---

## 1. Der große Überblick

SmartDesk besteht aus zwei komplett getrennten Programmen, die über HTTP miteinander reden:

- **Frontend** (`frontend/`) – eine Angular-Anwendung, läuft im Browser, zeigt die Oberfläche
- **Backend** (`backend/`) – eine FastAPI-Anwendung (Python), läuft als eigener Server, verwaltet Daten und Geschäftslogik

Diese Trennung nennt man **Client-Server-Architektur**. Warum nicht alles in einem? Weil so beide Teile unabhängig voneinander entwickelt, getestet und sogar auf unterschiedlichen Rechnern betrieben werden können – und weil es dem entspricht, wie echte Firmen-Software heute gebaut wird (wichtig fürs Portfolio).

Aktuell sind Frontend und Backend noch **nicht verbunden** – das Frontend zeigt noch Testdaten. Das Verbinden kommt in einer späteren Phase.

---

## 2. Tech-Stack: was und warum

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

FastAPI ist ein Python-Framework zum Bauen von REST-APIs (siehe Glossar unten). Vorteile, die für dieses Projekt den Ausschlag gaben:
- **Automatische Validierung** – du beschreibst Datenstrukturen einmal (die Pydantic-Schemas in `app/schemas/`), FastAPI prüft jede eingehende Anfrage automatisch dagegen.
- **Automatische Dokumentation** – die Swagger-UI unter `/docs` entsteht komplett automatisch aus deinem Code, ohne dass du sie separat pflegen musst.
- **Type Hints als echtes Werkzeug, nicht nur Deko** – FastAPI liest deine Python-Typannotationen (`def foo(x: int)`) und nutzt sie aktiv für Validierung und Dokumentation.
- Sehr verbreitet in echten Firmen aktuell, gutes Lernsignal fürs Portfolio.

### Warum PostgreSQL?

PostgreSQL ist eine **relationale** Datenbank – Daten liegen in Tabellen mit fest definierten Spalten, Tabellen können über **Fremdschlüssel** (Foreign Keys) miteinander verbunden werden (bei uns: ein Ticket "gehört" über `requester_id` zu einem User). Der Vorteil gegenüber einer dokumentbasierten DB (wie MongoDB oder Firebase Firestore, falls dir das was sagt): die Datenbank selbst erzwingt Konsistenz – ein Ticket kann z.B. gar nicht erst mit einer `requester_id` gespeichert werden, die auf keinen existierenden User zeigt. Das haben wir in Phase 2 direkt genutzt und getestet.

### Warum ein ORM (SQLAlchemy)?

Ein **ORM** (Object-Relational Mapper) übersetzt zwischen "Python-Objekten" und "Datenbank-Tabellenzeilen". Statt rohes SQL zu schreiben (`SELECT * FROM tickets WHERE ...`), schreibst du Python-Code (`db.execute(select(Ticket))`) und SQLAlchemy übersetzt das im Hintergrund in SQL. Vorteil: weniger Tippfehler-anfälliger String-SQL-Code, Autovervollständigung, und du bleibst in einer Sprache (Python) statt ständig zwischen Python und SQL zu wechseln.

### Warum Migrationen (Alembic)?

Ein Datenbank-Schema (welche Tabellen, welche Spalten gibt es) verändert sich über die Zeit – bei uns z.B. von "nur Tickets" zu "Tickets + Users mit Fremdschlüsseln". Eine **Migration** ist eine versionierte, nachvollziehbare Beschreibung so einer Änderung (ähnlich wie ein Git-Commit, nur für die Datenbankstruktur statt für Code). Alembic verwaltet diese Migrationen als Python-Dateien in `backend/alembic/versions/`. Der große Vorteil: man kann eine Migration **rückgängig machen** (`downgrade`) und **nachvollziehen**, wer wann was am Schema geändert hat – bei uns in Phase 1 und 2 sogar mit echten Bugs, die wir beim Testen gefunden und gefixt haben (siehe die Kommentare in den Migrationsdateien selbst).

### Warum Docker/Docker Compose?

Kurzfassung (ausführlich haben wir das im Chat besprochen): Docker sorgt dafür, dass Backend und Datenbank **isoliert und reproduzierbar** laufen, ohne dass du Python/PostgreSQL manuell auf Windows installieren musst. `docker compose up` startet beides mit einem Befehl. Mehr dazu im Glossar unten ("Container", "Image", "Kernel").

### Warum JWT + bcrypt für Auth?

- **bcrypt** hasht Passwörter absichtlich langsam (siehe Glossar), damit gestohlene Passwort-Hashes nicht in Sekunden durch Ausprobieren geknackt werden können.
- **JWT** merkt sich "wer eingeloggt ist", ohne dass der Server sich selbst was merken muss (siehe Glossar) – skaliert besser und ist der heute übliche Standard für APIs.

---

## 3. Glossar: die wichtigsten Konzepte

### REST-API
Eine Schnittstelle, über die zwei Programme per HTTP miteinander reden – mit festen "Verben" (`GET` = lesen, `POST` = erstellen, `PATCH` = teilweise ändern, `DELETE` = löschen) und URLs, die *Ressourcen* beschreiben (`/tickets`, `/tickets/5`). Unser Backend stellt so eine API bereit, das Frontend wird sie später aufrufen.

### Container, Image, Kernel (kurz)
- Ein **Image** ist ein unveränderlicher Bauplan (dein Code + alle Abhängigkeiten + eine Mini-Betriebssystem-Basis).
- Ein **Container** ist eine laufende Instanz eines Images – ein isolierter Prozess, der glaubt, er sei allein auf einem frischen System.
- Der **Kernel** ist der Kern eines Betriebssystems, der zwischen Programmen und Hardware vermittelt. Container nutzen spezielle Linux-Kernel-Features (Namespaces, cgroups) zur Isolation – deshalb brauchte Docker auf deinem Windows-Rechner eine Linux-VM im Hintergrund (WSL2), um überhaupt zu funktionieren (das Virtualisierungsproblem, das wir gemeinsam gefixt haben).

### ORM
Siehe oben ("Warum ein ORM"). Kurz: Python-Objekte statt roher SQL-Strings.

### Migration
Siehe oben ("Warum Migrationen"). Kurz: versionierte, nachvollziehbare Datenbank-Schema-Änderungen.

### Dependency Injection (DI)
Ein Muster, bei dem eine Funktion nicht selbst entscheidet, wie sie an eine Abhängigkeit (z.B. eine Datenbank-Session) kommt, sondern sie "von außen gereicht bekommt". Bei uns: `db: Session = Depends(get_db)` in jedem Router – FastAPI ruft `get_db()` automatisch auf und reicht das Ergebnis rein. Vorteil: die Funktion selbst bleibt einfach testbar und weiß nichts über die Details, wie die DB-Verbindung zustande kommt.

### Hashing, Salt, bcrypt
- **Hashing** = eine Einweg-Funktion: Eingabe rein, Ergebnis raus, aber nicht umkehrbar. `hash("geheim123")` → `"a3f5c8..."`, man kann daraus nicht zurückrechnen.
- **Salt** = eine zufällige Zeichenfolge, die vor dem Hashen mit reingemischt wird, damit gleiche Passwörter nicht denselben Hash ergeben.
- **bcrypt** = eine speziell für Passwörter gebaute, absichtlich langsame Hash-Funktion (im Gegensatz zu z.B. SHA256, das für Geschwindigkeit gebaut ist – schlecht für Passwörter).

### JWT (JSON Web Token)
Ein selbst-enthaltener, signierter Token, der "wer bist du und bis wann darfst du das sein" direkt in sich trägt (`sub` = User-ID, `role`, `exp` = Ablaufzeit). Der Server muss sich dafür nichts merken – er prüft nur die Signatur (mit einem geheimen `SECRET_KEY`) bei jeder Anfrage neu. Der Inhalt ist lesbar (nur Base64-kodiert, nicht verschlüsselt), aber nicht fälschbar ohne den geheimen Schlüssel.

### Enum (in der Datenbank)
Ein Feld, das nur eine feste Menge an Werten annehmen darf (bei uns z.B. `status`: nur `open`/`in_progress`/`resolved`/`closed`, keine beliebigen Strings). Postgres erzwingt das direkt auf Datenbankebene – ein ungültiger Wert wird von der DB abgelehnt, nicht nur vom Python-Code.

### `.env` / Umgebungsvariablen
Konfigurationswerte (Passwörter, geheime Schlüssel), die **außerhalb** des Codes in einer separaten, nicht eingecheckten Datei liegen – damit der Code öffentlich auf GitHub sein kann, ohne Geheimnisse preiszugeben. Ausführlich im Chat besprochen.

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

---

## 5. Wichtige Datenmodell-Entscheidungen

**Warum drei Rollen (`employee`/`agent`/`admin`) statt z.B. nur "Nutzer"?** Weil ein echtes ITSM-Tool (wie Jira Service Management) genau diese Trennung braucht: Melder ≠ Bearbeiter ≠ Administrator. Das macht die spätere Berechtigungslogik (wer darf ein Ticket schließen?) überhaupt erst sinnvoll.

**Warum 4 Ticket-Status statt 3 (`open`/`in_progress`/`resolved`/`closed`)?** Mit nur 3 Status ist "schließen" eine einzelne Aktion ohne Kontrolle. Mit `resolved` als Zwischenschritt gibt es eine echte Freigabe-Regel: ein Agent markiert als gelöst, aber nur ein Admin (oder der Melder durch Ablehnen) entscheidet über den nächsten Schritt.

**Warum die Status-Übergänge als einfaches Python-Dictionary statt einer State-Machine-Bibliothek?** Bei nur 4 Zuständen ist eine Bibliothek unnötige Komplexität – ein `dict[Status, set[Status]]` ist genauso mächtig, aber ohne zusätzliche Abhängigkeit komplett durchschaubar (kommt in Phase 4).

**Warum `requester_id` und `assignee_id` als zwei getrennte Felder?** Weil "wer hat's gemeldet" und "wer bearbeitet's gerade" unterschiedliche Dinge sind, die sich unabhängig voneinander ändern (ein Ticket kann den Bearbeiter wechseln, der Melder bleibt immer gleich).

---

## 6. Was noch fehlt (Kurz-Roadmap)

1. `/auth/register`, `/auth/login`-Endpunkte (die vorhandenen `security.py`-Bausteine verdrahten)
2. Ticket-Lifecycle-Regeln (wer darf welchen Status-Übergang machen)
3. Frontend an die echte API anbinden (Mock-Daten raus)
4. Kommentare/Zusatzfunktionen
5. Tests, Politur, Deployment-Feinschliff

Ausführlicher Phasenplan: siehe die Commit-Historie (`git log`) – jeder Phasen-Commit beschreibt, was dazukam und warum.
