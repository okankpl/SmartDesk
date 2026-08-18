import { Component, input } from '@angular/core';

export interface Ticket {
  title: string;
  status: 'open' | 'closed';
  priority: number;
}

@Component({
  selector: 'app-ticket-card',
  imports: [],
  templateUrl: './ticket-card.html',
  styleUrl: './ticket-card.scss'
})
export class TicketCard {
  readonly ticket = input.required<Ticket>();
}
