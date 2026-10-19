// Ein Vorher-/Nachher-Wert aus dem Ticketverlauf (1:1 wie FieldChange im
// Backend, siehe schemas/ticket_event.py).
export interface TicketEventChange {
  old: string | number | null;
  new: string | number | null;
  // Anzeigenamen liefert das Backend nur fuer assignee_id (Name statt
  // Nutzer-ID); bei allen anderen Feldern sind sie null.
  old_label?: string | null;
  new_label?: string | null;
}

export interface TicketEvent {
  id: number;
  actor_name: string;
  kind: 'created' | 'updated' | 'status_changed';
  changes: Record<string, TicketEventChange>;
  created_at: string;
}
