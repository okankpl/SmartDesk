# SmartDesk-Dokumentation

Der öffentliche Einstieg ist das [Projekt-README](../README.md): Demo starten, Funktionen ausprobieren und Prüfungen ausführen. Hier stehen die technischen Details. Zum Verstehen zuerst die Architektur lesen, bei Workflowfragen die Entscheidungen und für einen eigenen Server die Betriebsanleitung.

| Dokument | Inhalt |
| --- | --- |
| [Projekt-README](../README.md) | Demo starten, Funktionen, Technologieüberblick, Prüfungen und Grenzen |
| [Architektur und Konzepte](architektur-und-konzepte.md) | Anforderungen, Bausteine und technische Begründungen |
| [Workflow-, Historien- und Versionsentscheidungen](entscheidungen-workflow-und-historie.md) | Rollenmatrix, Transaktionen, konkurrierende Änderungen und Kompromisse |
| [Deployment und Betrieb](deployment.md) | Eigene Zielumgebung, HTTPS, Konfiguration, Migrationen und Backups |

## Was auf GitHub sichtbar ist

Das Repository ist öffentlich, einschließlich seiner Git-Historie. Es enthält Quellcode, Tests, Dokumentation und reproduzierbare Betriebskonfiguration, aber keine echten Zugangsdaten.

| Bereich | Veröffentlichung |
| --- | --- |
| `backend/`, `frontend/`, Tests und Migrationen | Öffentlich, ohne Abhängigkeiten und Build-Ausgaben |
| `README.md`, `docs/`, `scripts/`, Compose-Dateien, Workflows | Öffentlich: Projektdokumentation und reproduzierbarer Betrieb |
| `.env.example` und dokumentierte Demo-/Testwerte | Öffentlich: Vorlagen und absichtlich bekannte lokale Beispieldaten, keine echten Zugangsdaten |
| `notes/` | Nur lokal: persönliche Arbeitsnotizen, nicht Teil des Repositorys |
| `.env`, Backups, `tmp/`, `output/`, Caches und Testberichte | Ignoriert; nicht für die Veröffentlichung vorgesehen |

Die Regeln stehen in [.gitignore](../.gitignore). Sie verhindern das normale Hinzufügen neuer Dateien, entfernen aber keine bereits getrackten Dateien. Ignorierte Dateien sind außerdem kein verschlüsselter Speicher und werden nicht durch Git gesichert. Echte Zugangsdaten dürfen nie committed werden. Bei einer versehentlichen Veröffentlichung müssen sie widerrufen beziehungsweise ersetzt werden; ein späterer Löschcommit reicht nicht.

## Gültigkeit

Abgeglichen am **19.10.2026**, einschließlich Ticketeditor, Migration `b42e8f19a620`, Redis-gestützter Login-Drosselung und Bearbeiternamen im Änderungsverlauf. Es ist keine serverseitige Suche/Pagination und kein Passwort-Reset implementiert. Ein öffentliches Deployment wird nicht vorausgesetzt.

Die Textbeispiele bilden den Projektstand dieses Datums ab. Konkrete Frameworkabhängigkeiten stehen in den Paketdateien; Quellcode und Tests müssen bei späteren Änderungen erneut mit den Erklärungen abgeglichen werden.

## Prüfung

```powershell
# Im Projektverzeichnis, nach Installation der Frontend-Abhängigkeiten:
node --test scripts/check-docs.test.mjs
node scripts/check-docs.mjs
```

Der Prüfer kontrolliert lokale Verweise und verhindert Links aus öffentlichen Dokumenten auf lokale Privatbereiche. Lokale, nicht veröffentlichte Notizen lassen sich mit `node scripts/check-docs.mjs --include-private` zusätzlich prüfen. Inhaltliche Korrektheit und sinnvolle Diagramme bleiben Teil des Reviews.
