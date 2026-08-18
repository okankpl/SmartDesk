import { Component, computed, signal } from '@angular/core';
import { TicketCard, type Ticket } from './ticket-card/ticket-card';

@Component({
  selector: 'app-dashboard',
  imports: [TicketCard],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.scss'],
})
export class Dashboard {
  // Gemeinsamer Zustand für die Kennzahlen des Dashboards.
  protected readonly statistics = signal([
    { label: 'Offene Tickets', value: 12 },
    { label: 'Kritische Incidents', value: 2 },
    { label: 'Heute gelöst', value: 8 },
    { label: 'In Bearbeitung', value: 5 },
  ]);

  // Alle Tickets der Anwendung.
  protected readonly tickets = signal<Ticket[]>([
    { title: 'Login pruefen', status: 'open', priority: 1 },
    { title: 'Drucker einrichten', status: 'closed', priority: 3 },
    { title: 'Zugang anlegen', status: 'open', priority: 2 },
  ]);

  // Filtert automatisch alle offenen Tickets aus dem Ticket-Zustand.
  protected readonly openTickets = computed(() =>
    this.tickets().filter(ticket => ticket.status === 'open'),
  );

  // Gibt die Anzahl der offenen Tickets zurück.
  protected readonly openTicketCount = computed(() =>
    this.openTickets().length,
  );

  // Steuert, ob das Dashboard offene oder erledigte Tickets zeigt.
  protected readonly showCompletedTickets = signal(false);

  // Die sichtbare Liste wird aus dem aktuellen Ansichtsmodus abgeleitet.
  protected readonly visibleTickets = computed(() =>
    this.showCompletedTickets()
      ? this.tickets().filter(ticket => ticket.status === 'closed')
      : this.openTickets(),
  );

  protected toggleTicketView(): void {
    this.showCompletedTickets.update(showCompleted => !showCompleted);
  }
}
