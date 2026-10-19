import { Component, inject, input, resource } from '@angular/core';
import { DatePipe, KeyValuePipe } from '@angular/common';
import { firstValueFrom } from 'rxjs';
import { TicketsService } from '../../../core/tickets/tickets';

const LABELS: Record<string, string> = {
  open: 'Offen', in_progress: 'In Bearbeitung', resolved: 'Gelöst', closed: 'Geschlossen',
  low: 'Niedrig', medium: 'Mittel', high: 'Hoch', critical: 'Kritisch',
  status: 'Status', assignee_id: 'Bearbeiter', title: 'Titel', description: 'Beschreibung', priority: 'Priorität',
  created: 'Ticket erstellt', updated: 'Ticket geändert', status_changed: 'Status geändert',
};

@Component({
  selector: 'app-ticket-history',
  imports: [DatePipe, KeyValuePipe],
  template: `
    <section aria-label="Änderungsverlauf" class="history">
      <h3>Änderungsverlauf</h3>
      @if (history.error()) {
        <p role="alert">Der Verlauf konnte nicht geladen werden.</p>
        <button type="button" (click)="history.reload()">Erneut laden</button>
      } @else if (history.isLoading()) {
        <p role="status">Verlauf wird geladen…</p>
      } @else {
        <ol>
          @for (event of history.value(); track event.id) {
            <li>
              <div class="event-heading"><strong>{{ label(event.kind) }}</strong><time [attr.datetime]="event.created_at">{{ event.created_at | date: 'dd.MM.yyyy, HH:mm' }}</time></div>
              <span>{{ event.actor_name }}</span>
              @for (change of event.changes | keyvalue; track change.key) {
                <p class="change">{{ label(change.key) }}: {{ value(change.key, change.value.old, change.value.old_label) }} → {{ value(change.key, change.value.new, change.value.new_label) }}</p>
              }
            </li>
          } @empty {
            <li>Für dieses Ticket sind noch keine Änderungen erfasst.</li>
          }
        </ol>
      }
    </section>
  `,
  styles: `
    .history { border-top: 1px solid var(--border); padding-top: 1.2rem; color: var(--muted); font-size: 14px; }
    h3 { color: var(--text); font-size: 14px; margin: 0 0 1rem; }
    ol { list-style: none; margin: 0; padding: 0; display: grid; gap: 1rem; }
    li { border-left: 2px solid #b5d8cc; padding-left: .875rem; overflow-wrap: anywhere; }
    .event-heading { display: flex; flex-wrap: wrap; justify-content: space-between; gap: .25rem .75rem; }
    strong { color: #23312d; }
    time { font-size: .75rem; }
    .change { margin: .25rem 0 0; white-space: pre-wrap; max-height: 5rem; overflow: auto; }
    button { background: white; border: 1px solid #c8d3cc; border-radius: 4px; padding: .5rem .75rem; }
  `,
})
export class TicketHistory {
  readonly ticketId = input.required<number>();
  readonly revision = input(0);
  private readonly tickets = inject(TicketsService);
  protected readonly history = resource({
    params: () => ({ id: this.ticketId(), revision: this.revision() }),
    loader: ({ params }) => firstValueFrom(this.tickets.history(params.id)),
    defaultValue: [],
  });
  protected label(key: string): string { return LABELS[key] ?? key; }

  // Wandelt einen gespeicherten Wert in Anzeigetext um:
  // - Bearbeiter: der vom Backend mitgelieferte Name (vorher stand hier immer
  //   "Nutzer #3"); die ID nur noch als Rueckfall, falls es den Nutzer nicht mehr gibt.
  // - Status und Prioritaet: feste Schluessel mit deutscher Uebersetzung.
  // - Titel und Beschreibung: freier Text, unveraendert. Vorher wurde auch er
  //   uebersetzt - ein Titel "critical" erschien dann als "Kritisch".
  protected value(field: string, value: string | number | null, label?: string | null): string {
    if (value === null) return '—';
    if (field === 'assignee_id') return label ?? `Nutzer #${value}`;
    return field === 'status' || field === 'priority' ? this.label(String(value)) : String(value);
  }
}
