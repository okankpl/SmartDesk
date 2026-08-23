import { Component, computed, inject, resource, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { TicketsService } from '../../core/tickets/tickets';
import { TicketStatus } from '../../core/tickets/ticket';
import { TicketCard } from './ticket-card/ticket-card';

// Prueft, ob ein ISO-Datumsstring auf den heutigen Tag faellt (lokale
// Zeitzone) - fuer die "Heute gelöst"-Kennzahl. Vergleicht nur Jahr/Monat/Tag,
// nicht die Uhrzeit.
function isToday(isoDate: string | null): boolean {
  if (isoDate === null) {
    return false;
  }
  const date = new Date(isoDate);
  const now = new Date();
  return (
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  );
}

@Component({
  selector: 'app-dashboard',
  imports: [TicketCard],
  templateUrl: './dashboard.html',
  styleUrls: ['./dashboard.scss'],
})
export class Dashboard {
  private readonly ticketsService = inject(TicketsService);

  // resource() laedt Tickets von GET /tickets und haelt Lade-/Fehlerzustand
  // automatisch als Signals bereit (isLoading/error) - ohne resource() muesste
  // man diese beiden Zustaende von Hand mit eigenen Signals nachbauen.
  private readonly ticketsResource = resource({
    loader: () => firstValueFrom(this.ticketsService.list()),
  });

  // .value() ist bis zum ersten erfolgreichen Laden undefined - mit ?? [] hat
  // der Rest der Komponente immer ein echtes Array, ohne ueberall extra auf
  // undefined pruefen zu muessen.
  protected readonly tickets = computed(() => this.ticketsResource.value() ?? []);
  protected readonly isLoadingTickets = this.ticketsResource.isLoading;
  protected readonly ticketsError = this.ticketsResource.error;

  // Filtert automatisch alle offenen Tickets aus dem Ticket-Zustand.
  protected readonly openTickets = computed(() =>
    this.tickets().filter((ticket) => ticket.status === 'open'),
  );
  // Gibt die Anzahl der offenen Tickets zurück.
  protected readonly openTicketCount = computed(() => this.openTickets().length);

  // Filtert alle Tickets, die sich aktuell in Bearbeitung befinden.
  protected readonly inProgressTickets = computed(() =>
    this.tickets().filter((ticket) => ticket.status === 'in_progress'),
  );
  // Gibt die Anzahl der Tickets in Bearbeitung zurück.
  protected readonly inProgressTicketCount = computed(() => this.inProgressTickets().length);

  // "Kritische Incidents": noch NICHT erledigte Tickets (offen oder in
  // Bearbeitung) mit Priorität "critical" - ein bereits geschlossenes
  // kritisches Ticket ist kein aktiver Incident mehr.
  protected readonly criticalIncidentCount = computed(
    () =>
      this.tickets().filter(
        (ticket) =>
          ticket.priority === 'critical' && (ticket.status === 'open' || ticket.status === 'in_progress'),
      ).length,
  );

  // "Heute gelöst": Tickets, deren resolved_at auf den heutigen Tag faellt.
  // Bewusst resolved_at, nicht closed_at - "gelöst" ist im Datenmodell ein
  // eigener, fachlich anderer Zeitpunkt als "final geschlossen" (siehe
  // Architektur-Doku, Abschnitt 5).
  protected readonly resolvedTodayCount = computed(
    () => this.tickets().filter((ticket) => isToday(ticket.resolved_at)).length,
  );

  // Kennzahlen für die Statistik-Karten - alle vier jetzt aus echten Ticketdaten
  // berechnet.
  protected readonly statistics = computed(() => [
    { label: 'Offene Tickets', value: this.openTicketCount() },
    { label: 'Kritische Incidents', value: this.criticalIncidentCount() },
    { label: 'Heute gelöst', value: this.resolvedTodayCount() },
    { label: 'In Bearbeitung', value: this.inProgressTicketCount() },
  ]);

  // Die vier Ansichten, zwischen denen im Ticket-Bereich gewechselt werden kann
  // (entspricht den vier Status im Ticket-Lifecycle). Eine einzige Quelle für
  // Tab-Beschriftung, Abschnittsüberschrift und Filterlogik.
  protected readonly viewTabs: { status: TicketStatus; label: string }[] = [
    { status: 'open', label: 'Offene Tickets' },
    { status: 'in_progress', label: 'In Bearbeitung' },
    { status: 'resolved', label: 'Gelöste Tickets' },
    { status: 'closed', label: 'Geschlossene Tickets' },
  ];

  // Welcher Status ist gerade in der Ticket-Ansicht aktiv.
  protected readonly activeView = signal<TicketStatus>('open');

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
  protected setActiveView(status: TicketStatus): void {
    this.activeView.set(status);
  }
}
