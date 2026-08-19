import { Component, computed, input } from '@angular/core';

export interface Ticket {
  title: string;
  status: 'open' | 'closed'| 'in-progress';
  priority: number;
}

// Deutsche Beschriftung für jeden Ticket-Status im Status-Badge.
const STATUS_LABELS: Record<Ticket['status'], string> = {
  open: 'Offen',
  'in-progress': 'In Bearbeitung',
  closed: 'Erledigt',
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
}
