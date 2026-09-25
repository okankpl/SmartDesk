// Feldnamen 1:1 wie CommentRead im Backend (schemas/comment.py), snake_case
// statt camelCase - dieselbe Regel wie bei Ticket (ticket.ts) und CurrentUser
// (auth.ts), damit Frontend und Backend nicht still auseinanderlaufen.
//
// Name bewusst "TicketComment" statt einfach "Comment": "Comment" ist in
// TypeScript bereits ein GLOBALER Typ - er beschreibt einen HTML-Kommentar-
// knoten (<!-- ... -->) aus der Browser-DOM-API und ist ueberall ohne Import
// verfuegbar. Ein eigenes Interface gleichen Namens wuerde diesen Typ in jeder
// Datei, die es importiert, "ueberdecken" (Shadowing) - das funktioniert zwar,
// fuehrt aber zu verwirrenden Fehlermeldungen, sobald man den Import einmal
// vergisst (dann greift still der DOM-Typ und TypeScript meckert ueber
// fehlende Felder wie "body", die man doch "eindeutig" definiert hat).
export interface TicketComment {
  id: number;
  ticket_id: number;
  // Nur die ID, kein Name - das Backend liefert (noch) keinen Autorennamen mit,
  // siehe authorLabel() in ticket-card.ts, wie das im Popup angezeigt wird.
  author_id: number;
  body: string;
  // ISO-8601-String wie bei Ticket.created_at, kein Date-Objekt.
  created_at: string;
}
