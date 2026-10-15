import { TicketPriority, TicketStatus } from './ticket';

export const STATUS_LABELS: Record<TicketStatus, string> = {
  open: 'Offen', in_progress: 'In Bearbeitung', resolved: 'Gelöst', closed: 'Geschlossen',
};
export const PRIORITY_LABELS: Record<TicketPriority, string> = {
  low: 'Niedrig', medium: 'Mittel', high: 'Hoch', critical: 'Kritisch',
};
