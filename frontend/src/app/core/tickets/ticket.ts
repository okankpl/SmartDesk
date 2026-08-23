// Feldnamen und Enum-Werte 1:1 wie im Backend-JSON (siehe TicketRead in
// schemas/ticket.py, TicketStatus/TicketPriority in models/ticket.py) - keine
// eigene Uebersetzung, aus genau dem Grund, der beim CurrentUser-Interface
// schon einmal einen Laufzeitfehler verursacht hat (siehe Architektur-Doku,
// Abschnitt 8 "API-Feldnamen 1:1 uebernommen").

export type TicketStatus = 'open' | 'in_progress' | 'resolved' | 'closed';
export type TicketPriority = 'low' | 'medium' | 'high' | 'critical';

export interface Ticket {
  id: number;
  title: string;
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
