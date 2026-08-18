import { Component, signal } from '@angular/core';
import { Ticket, TicketCard } from './ticket-card/ticket-card';

@Component({
  selector: 'app-dashboard',
  imports: [TicketCard],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss'
})
export class Dashboard {
  // Gemeinsamer Zustand für die Kennzahlen des Dashboards
  protected readonly statistics = signal([
    { label: 'Offene Tickets', value: 12 },
    { label: 'Kritische Incidents', value: 2 },
    { label: 'Heute gelöst', value: 8 },
    { label: 'In Bearbeitung', value: 5 }
  ]);

  protected readonly tickets = signal<Ticket[]>([
    { title: 'Login pruefen', status: 'open', priority: 1 },
    { title: 'Drucker einrichten', status: 'closed', priority: 3 },
    { title: 'Zugang anlegen', status: 'open', priority: 2 }
  ]);
}
