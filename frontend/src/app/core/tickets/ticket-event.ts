export interface TicketEvent {
  id: number;
  actor_name: string;
  kind: 'created' | 'updated' | 'status_changed';
  changes: Record<string, { old: string | number | null; new: string | number | null }>;
  created_at: string;
}
