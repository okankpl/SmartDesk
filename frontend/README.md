# SmartDesk Frontend

Das Frontend von SmartDesk ist eine Angular-Anwendung. Der Code bleibt bewusst in
kleinen, klar getrennten Komponenten, damit jede Datei eine gut erkennbare Aufgabe
hat.

## Projektstruktur

```text
src/app/
	app.routes.ts                 Routing der Anwendung
	layout/main-layout/           Gemeinsame App-Shell mit Navigation
	pages/dashboard/              Dashboard-Seite
		dashboard.ts                Zustand und Logik des Dashboards
		dashboard.html              Darstellung des Dashboards
		dashboard.scss              Styling des Dashboards
		ticket-card/                Wiederverwendbare Ticket-Komponente
```

## Arbeitsweise im Projekt

- Eine Komponente bekommt eine überschaubare Aufgabe.
- HTML enthält die Darstellung, TypeScript den Zustand und die Logik, SCSS das Styling.
- Neue oder komplexere Logik erhält einen kurzen Kommentar, der den Zweck erklärt.
- Offensichtliche Syntax wird nicht kommentiert.
- Verständliche Namen sind wichtiger als möglichst kurze Namen.
- Daten werden möglichst typisiert, zum Beispiel mit einem `interface`.

## Wichtige TypeScript- und Angular-Grundlagen

### Array und Objekt

Ein Array ist eine geordnete Liste. Ein Objekt beschreibt einen einzelnen Datensatz:

```ts
const tickets = [
	{ title: 'Login pruefen', status: 'open', priority: 1 },
	{ title: 'Drucker einrichten', status: 'closed', priority: 3 }
];

const firstTicket = tickets[0];
const title = firstTicket.title;
```

### `map`

`map` wandelt jedes Element um und erstellt ein neues Array gleicher Länge:

```ts
const titles = tickets.map(ticket => ticket.title);
```

### `filter`

`filter` behält alle Elemente, für die die Bedingung `true` ergibt:

```ts
const openTickets = tickets.filter(ticket => ticket.status === 'open');
```

### `find`

`find` gibt nur das erste passende Element zurück. Wenn kein Element passt, ist das
Ergebnis `undefined`:

```ts
const firstOpenTicket = tickets.find(ticket => ticket.status === 'open');
```

### `signal`

Ein Signal hält reaktive Daten. Mit `tickets()` wird der aktuelle Wert gelesen:

```ts
protected readonly tickets = signal<Ticket[]>([]);
```

Im Template kann Angular auf Änderungen reagieren und die Anzeige aktualisieren.

### `computed`

`computed` erstellt einen Wert aus anderen Signals. Der Wert wird automatisch neu
berechnet, wenn sich eine verwendete Quelle ändert:

```ts
const openTickets = computed(() =>
	tickets().filter(ticket => ticket.status === 'open')
);
```

Ein `computed`-Signal wird wie ein normales Signal mit `openTickets()` gelesen.
Das Dashboard nutzt dieses Prinzip, um zwischen offenen und erledigten Tickets zu
wechseln, ohne die Ticketdaten doppelt zu speichern.

### Angular-Template-Syntax

Mit `@for` wird eine Liste dargestellt. `track` hilft Angular dabei, einzelne Einträge
bei Änderungen wiederzuerkennen:

```html
@for (ticket of tickets(); track ticket.title) {
	<app-ticket-card [ticket]="ticket" />
}
```

`[ticket]` übergibt das aktuelle Ticket an den Input der Kindkomponente.

## Entwicklung

This project was generated using [Angular CLI](https://github.com/angular/angular-cli) version 22.1.4.

## Development server

To start a local development server, run:

```bash
npm start
```

Once the server is running, open your browser and navigate to `http://localhost:4200/`. The application will automatically reload whenever you modify any of the source files.

## Build prüfen

Vor einem Abschluss sollte der Build ohne Fehler durchlaufen:

```bash
npm run build
```

## Code scaffolding

Angular CLI includes powerful code scaffolding tools. To generate a new component, run:

```bash
ng generate component component-name
```

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
ng generate --help
```

## Building

To build the project run:

```bash
ng build
```

This will compile your project and store the build artifacts in the `dist/` directory. By default, the production build optimizes your application for performance and speed.

## Running unit tests

To execute unit tests with the [Vitest](https://vitest.dev/) test runner, use the following command:

```bash
ng test
```

## Running end-to-end tests

For end-to-end (e2e) testing, run:

```bash
ng e2e
```

Angular CLI does not come with an end-to-end testing framework by default. You can choose one that suits your needs.

## Additional Resources

For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.
