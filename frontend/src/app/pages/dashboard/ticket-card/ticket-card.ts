import { Component, computed, input } from '@angular/core';
import { Ticket, TicketPriority, TicketStatus } from '../../../core/tickets/ticket';

// Deutsche Beschriftung für jeden Ticket-Status im Status-Badge.
const STATUS_LABELS: Record<TicketStatus, string> = {
  open: 'Offen',
  in_progress: 'In Bearbeitung',
  resolved: 'Gelöst',
  closed: 'Geschlossen',
};

// Deutsche Beschriftung für jede Priorität im Prioritäts-Badge.
const PRIORITY_LABELS: Record<TicketPriority, string> = {
  low: 'Niedrig',
  medium: 'Mittel',
  high: 'Hoch',
  critical: 'Kritisch',
};

@Component({
  selector: 'app-ticket-card',
  imports: [],
  templateUrl: './ticket-card.html',
  styleUrl: './ticket-card.scss'
})
export class TicketCard {
  readonly ticket = input.required<Ticket>();

  // Beschriftung für das Status-Badge, abgeleitet aus dem aktuellen Ticket-Status.
  protected readonly statusLabel = computed(() => STATUS_LABELS[this.ticket().status]);

  // Beschriftung für das Prioritäts-Badge, abgeleitet aus der aktuellen Priorität.
  protected readonly priorityLabel = computed(() => PRIORITY_LABELS[this.ticket().priority]);
}
