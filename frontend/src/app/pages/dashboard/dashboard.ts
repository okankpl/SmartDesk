import { Component, computed, inject, resource, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { LucidePlus, LucideX, LucideRefreshCw, LucideList, LucideLayoutGrid, LucideInbox, LucideTriangleAlert, LucideCircleCheck } from '@lucide/angular';

import { TicketsService } from '../../core/tickets/tickets';
import { Ticket, TicketPriority, TicketStatus } from '../../core/tickets/ticket';
import { Auth } from '../../core/auth/auth';
import { TicketCard } from './ticket-card/ticket-card';
import { TicketFilters, SortOrder } from './ticket-filters/ticket-filters';
import { TicketStatistics } from './ticket-statistics/ticket-statistics';

type TicketView = TicketStatus | 'all';
const PRIORITY_ORDER: Record<TicketPriority, number> = { low: 0, medium: 1, high: 2, critical: 3 };

function isToday(value: string | null): boolean {
  if (!value) return false;
  return new Date(value).toDateString() === new Date().toDateString();
}

@Component({
  selector: 'app-dashboard',
  imports: [TicketCard, TicketFilters, TicketStatistics, RouterLink, DatePipe, LucidePlus, LucideX, LucideRefreshCw, LucideList, LucideLayoutGrid, LucideInbox, LucideTriangleAlert, LucideCircleCheck],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class Dashboard {
  private readonly ticketsService = inject(TicketsService);
  private readonly currentUser = inject(Auth).currentUser;
  private readonly route = inject(ActivatedRoute);
  private readonly lastSuccessfulTickets = signal<Ticket[] | null>(null);
  protected readonly lastUpdated = signal<Date | null>(null);
  protected readonly isSupport = computed(() => ['agent', 'admin'].includes(this.currentUser()?.role ?? ''));
  protected readonly search = signal('');
  protected readonly priorityFilter = signal<TicketPriority | ''>('');
  protected readonly assignmentFilter = signal<'all' | 'mine' | 'unassigned'>('all');
  protected readonly sortOrder = signal<SortOrder>('priority');
  protected readonly displayMode = signal<'list' | 'cards'>('list');
  protected readonly activeView = signal<TicketView>('open');
  protected readonly hasFilters = computed(() => !!this.search().trim() || !!this.priorityFilter() || this.assignmentFilter() !== 'all');
  protected readonly createdId = Number(this.route.snapshot.queryParamMap.get('created')) || null;
  protected readonly announcement = signal<string | null>(
    this.createdId ? 'Ticket SD-' + String(this.createdId).padStart(4, '0') + ' wurde erstellt.' : null,
  );

  private readonly ticketsResource = resource({
    // params: haengt das Laden an das angemeldete Konto. Wechselt es (Rollen-
    // wechsel in der Demo), laedt resource() die Liste automatisch neu - ohne
    // dass das Dashboard dafuer neu erzeugt werden muss. Als Objekt verpackt:
    // gibt params undefined zurueck, laedt resource() gar nicht erst.
    params: () => ({ userId: this.currentUser()?.id ?? null }),
    loader: async () => {
      const tickets = await firstValueFrom(this.ticketsService.list());
      this.lastSuccessfulTickets.set(tickets);
      this.lastUpdated.set(new Date());
      return tickets;
    },
  });

  // Schlaegt ein Neuladen fehl, bleibt die zuletzt erfolgreich geladene Liste
  // sichtbar (hasValue() ist im Fehlerzustand false).
  protected readonly tickets = computed(() => this.ticketsResource.hasValue()
    ? this.ticketsResource.value() : this.lastSuccessfulTickets() ?? []);
  protected readonly isInitialLoading = computed(() => this.ticketsResource.isLoading() && this.lastSuccessfulTickets() === null);
  protected readonly isRefreshing = this.ticketsResource.isLoading;
  protected readonly ticketsError = this.ticketsResource.error;

  protected readonly openTickets = computed(() => this.tickets().filter(ticket => ticket.status === 'open'));
  protected readonly openTicketCount = computed(() => this.openTickets().length);
  protected readonly inProgressTickets = computed(() => this.tickets().filter(ticket => ticket.status === 'in_progress'));
  protected readonly inProgressTicketCount = computed(() => this.inProgressTickets().length);
  protected readonly criticalIncidentCount = computed(() => this.tickets().filter(ticket =>
    ticket.priority === 'critical' && ['open', 'in_progress'].includes(ticket.status)).length);
  protected readonly resolvedTodayCount = computed(() => this.tickets().filter(ticket => isToday(ticket.resolved_at)).length);

  protected readonly viewTabs: { status: TicketView; label: string }[] = [
    { status: 'all', label: 'Alle Tickets' },
    { status: 'open', label: 'Offene Tickets' },
    { status: 'in_progress', label: 'In Bearbeitung' },
    { status: 'resolved', label: 'Gelöste Tickets' },
    { status: 'closed', label: 'Geschlossene Tickets' },
  ];
  protected readonly activeViewLabel = computed(() => this.viewTabs.find(tab => tab.status === this.activeView())!.label);

  // Zaehler und Ergebnisliste nutzen dieselben Such- und Filterkriterien,
  // unabhaengig davon, welcher Status-Tab gerade aktiv ist.
  private readonly filteredTickets = computed(() => {
    const query = this.search().trim().toLocaleLowerCase('de');
    return this.tickets().filter(ticket => {
      const text = [ticket.title, ticket.description ?? '', ticket.requester_name ?? '', ticket.assignee_name ?? '', '#' + ticket.id, 'SD-' + String(ticket.id).padStart(4, '0')].join(' ').toLocaleLowerCase('de');
      return (!query || text.includes(query))
        && (!this.priorityFilter() || ticket.priority === this.priorityFilter())
        && (this.assignmentFilter() !== 'mine' || ticket.assignee_id === this.currentUser()?.id)
        && (this.assignmentFilter() !== 'unassigned' || ticket.assignee_id === null);
    });
  });
  protected readonly visibleTickets = computed(() => {
    const result = this.filteredTickets().filter(ticket => this.activeView() === 'all' || ticket.status === this.activeView());
    return result.sort((a, b) => {
      if (this.sortOrder() === 'newest') return Date.parse(b.created_at) - Date.parse(a.created_at) || b.id - a.id;
      if (this.sortOrder() === 'oldest') return Date.parse(a.created_at) - Date.parse(b.created_at) || a.id - b.id;
      return PRIORITY_ORDER[b.priority] - PRIORITY_ORDER[a.priority] || Date.parse(a.created_at) - Date.parse(b.created_at) || a.id - b.id;
    });
  });

  protected countForStatus(status: TicketView): number {
    return this.filteredTickets().filter(ticket => status === 'all' || ticket.status === status).length;
  }
  protected setActiveView(status: TicketView): void { this.activeView.set(status); }
  protected resetFilters(): void {
    this.search.set('');
    this.priorityFilter.set('');
    this.assignmentFilter.set('all');
  }
  protected showAllTickets(): void { this.resetFilters(); this.activeView.set('all'); }
  protected reloadTickets(): void { this.ticketsResource.reload(); }
  protected onTicketChanged(): void {
    this.announcement.set('Die Änderungen wurden gespeichert.');
    this.reloadTickets();
  }
}
