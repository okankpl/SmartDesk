import { Component, computed, signal } from '@angular/core';
import { TicketCard, type Ticket } from './ticket-card/ticket-card';

@Component({
  selector: 'app-dashboard',
  imports: [TicketCard],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.scss'],
})
export class Dashboard {
  // Alle Tickets der Anwendung.
  protected readonly tickets = signal<Ticket[]>([
    { title: 'Login pruefen', status: 'in-progress', priority: 1 },
    { title: 'Drucker einrichten', status: 'closed', priority: 3 },
    { title: 'Zugang anlegen', status: 'open', priority: 2 },
  ]);

  // Filtert automatisch alle offenen Tickets aus dem Ticket-Zustand.
  protected readonly openTickets = computed(() =>
    this.tickets().filter((ticket) => ticket.status === 'open'),
  );
  // Gibt die Anzahl der offenen Tickets zurück.
  protected readonly openTicketCount = computed(() => this.openTickets().length);

  // Filtert alle Tickets, die sich aktuell in Bearbeitung befinden.
  protected readonly inProgressTickets = computed(() =>
    this.tickets().filter((ticket) => ticket.status === 'in-progress'),
  );
  // Gibt die Anzahl der Tickets in Bearbeitung zurück.
  protected readonly inProgressTicketCount = computed(() => this.inProgressTickets().length);

  // Kennzahlen für die Statistik-Karten. "Offene Tickets" und "In Bearbeitung" werden live aus
  // den echten Ticketdaten berechnet. Für "Kritische Incidents" und "Heute gelöst" gibt es noch
  // keine passenden Datenfelder (z. B. eine Kritikalität oder ein Erledigungsdatum), daher
  // bleiben sie vorerst feste Platzhalterwerte.
  protected readonly statistics = computed(() => [
    { label: 'Offene Tickets', value: this.openTicketCount() },
    { label: 'Kritische Incidents', value: 2 },
    { label: 'Heute gelöst', value: 8 },
    { label: 'In Bearbeitung', value: this.inProgressTicketCount() },
  ]);

  // Die drei Ansichten, zwischen denen im Ticket-Bereich gewechselt werden kann. Eine einzige
  // Quelle für Tab-Beschriftung, Abschnittsüberschrift und Filterlogik.
  protected readonly viewTabs: { status: Ticket['status']; label: string }[] = [
    { status: 'open', label: 'Offene Tickets' },
    { status: 'in-progress', label: 'In Bearbeitung' },
    { status: 'closed', label: 'Erledigte Tickets' },
  ];

  // Welcher Status ist gerade in der Ticket-Ansicht aktiv.
  protected readonly activeView = signal<Ticket['status']>('open');

  // Beschriftung der aktuell aktiven Ansicht für die Abschnittsüberschrift.
  protected readonly activeViewLabel = computed(() => {
    const activeTab = this.viewTabs.find((tab) => tab.status === this.activeView());
    return activeTab ? activeTab.label : '';
  });

  // Die sichtbare Ticketliste wird aus dem aktuell aktiven Status abgeleitet.
  protected readonly visibleTickets = computed(() =>
    this.tickets().filter((ticket) => ticket.status === this.activeView()),
  );

  // Wechselt die aktive Ansicht auf den übergebenen Status.
  protected setActiveView(status: Ticket['status']): void {
    this.activeView.set(status);
  }
}
