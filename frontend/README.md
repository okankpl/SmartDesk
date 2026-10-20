# SmartDesk Frontend

Angular-Anwendung mit Signals, typisierten HTTP-Services und getrennten Seiten- und Darstellungskomponenten. Den vollständigen Stack und die Demo beschreibt das [Projekt-README](../README.md); technische Hintergründe stehen in der [Dokumentationsübersicht](../docs/README.md).

## Lokal entwickeln

Voraussetzung: Node.js gemäß [.nvmrc](.nvmrc). Das Entwicklungsbackend muss unter `http://localhost:8000` laufen. Alle folgenden Befehle im Verzeichnis `frontend/` ausführen:

```bash
npm ci
npm start
```

Oberfläche: `http://localhost:4200`. Die API-Adressen stehen in [src/environments](src/environments) und [api-url.ts](src/app/core/api-url.ts). Der Produktionsbuild verwendet `/api` über den Reverse-Proxy.

## Prüfungen

```bash
# Komponenten und Services einmalig testen.
npm test -- --watch=false

# TypeScript, Templates und Build-Budgets prüfen.
npm run build

# Browser-Tests gegen die laufende Container-Demo auf localhost:8080.
npx playwright install chromium
npm run test:e2e
```

## Orientierung im Code

| Pfad | Aufgabe |
| --- | --- |
| [src/app/core](src/app/core) | Authentifizierung, Demo-Konfiguration, HTTP-Services und gemeinsame Datentypen |
| [src/app/layout](src/app/layout) | Navigation, gemeinsamer Seitenrahmen und Demo-Leiste mit Rollenwechsel |
| [src/app/pages](src/app/pages) | Anmeldung, Registrierung, Ticketerstellung und Dashboard |
| [src/app/pages/dashboard](src/app/pages/dashboard) | Warteschlange, Detaildialog, Editor, Kommentare und Historie |
| [e2e](e2e) | Playwright-Abläufe für Desktop und Mobile |

Tests liegen neben den Komponenten und Services als `*.spec.ts`. Der Build landet in `dist/frontend/browser`; generierte Ausgaben und Browser-Testberichte werden nicht committed.
