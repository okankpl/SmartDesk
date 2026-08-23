// Feldnamen und Enum-Werte 1:1 wie im Backend-JSON (siehe TicketRead in
// schemas/ticket.py, TicketStatus/TicketPriority in models/ticket.py) - keine
// eigene Uebersetzung, aus genau dem Grund, der beim CurrentUser-Interface
// schon einmal einen Laufzeitfehler verursacht hat (siehe Architektur-Doku,
// Abschnitt 8 "API-Feldnamen 1:1 uebernommen").

// "Union Type" (mit | getrennte Werte): TypeScript erlaubt fuer eine Variable
// dieses Typs NUR genau diese vier String-Werte, nichts anderes - vergleichbar
// mit dem Python-Enum TicketStatus im Backend, nur ohne eigene Klasse. Der
// Compiler meldet schon beim Schreiben des Codes einen Fehler, wenn irgendwo
// z.B. "opne" (Tippfehler) oder "in-progress" (Bindestrich statt Unterstrich)
// stehen wuerde.
export type TicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed';
export type TicketPriority = 'low' | 'medium' | 'high' | 'critical';

// "interface" beschreibt die Form eines Objekts (welche Felder mit welchen
// Typen es haben MUSS), erzeugt aber selbst keine Laufzeit-Klasse - reine
// Compile-Zeit-Pruefung. Vergleichbar mit einem Pydantic-Schema im Backend,
// nur dass TypeScript NICHT wie Pydantic zur Laufzeit prueft, ob ein von
// HttpClient empfangenes JSON-Objekt wirklich zu diesem Interface passt (das
// ist reine Behauptung/Annahme) - siehe die Lektion dazu in der Architektur-Doku.
export interface Ticket {
  id: number;
  title: string;
  // "string | null": das Feld ist entweder ein String ODER genau der Wert
  // null - TypeScript zwingt einen dadurch, an jeder Stelle, die description
  // benutzt, auch den null-Fall zu behandeln (siehe z.B. das "|| 'Keine
  // Beschreibung...'" in ticket-card.html).
  description: string | null;
  status: TicketStatus;
  priority: TicketPriority;
  requester_id: number;
  assignee_id: number | null;
  // ISO-8601-Strings, keine Date-Objekte - HttpClient parst JSON-Strings nicht
  // automatisch zu Date, das muesste man bei Bedarf selbst tun (new Date(...)).
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
  closed_at: string | null;
}
