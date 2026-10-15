import { Component, computed, inject, input, model, output, resource, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { CurrentUser } from '../../../core/auth/auth';
import { API_URL } from '../../../core/api-url';
import { Ticket } from '../../../core/tickets/ticket';
import { TicketsService } from '../../../core/tickets/tickets';
import { errorMessageFor } from '../../../core/http-error-message';

@Component({
  selector: 'app-ticket-assignment',
  template: `
    @if (users.error()) {
      <p role="alert">Bearbeiter konnten nicht geladen werden.</p>
      <button type="button" (click)="users.reload()">Erneut laden</button>
    } @else {
      <form (submit)="save($event)">
        <div class="assignment-field"><label [for]="'assignee-' + ticket().id">Bearbeiter zuweisen</label>
          <select [id]="'assignee-' + ticket().id" name="assignee_id" [value]="ticket().assignee_id ?? ''" [disabled]="disabled() || users.isLoading() || busy()">
            <option value="" [disabled]="ticket().status !== 'open'">Nicht zugewiesen</option>
            @for (person of agents(); track person.id) { <option [value]="person.id">{{ person.full_name }}</option> }
          </select>
        </div>
        <button type="submit" class="button" [disabled]="disabled() || users.isLoading() || busy()">{{ busy() ? 'Wird gespeichert…' : 'Zuweisen' }}</button>
      </form>
    }
    @if (error()) { <p role="alert">{{ error() }}</p> }
  `,
  styles: `
    form { display: grid; gap: .6rem; }
    .assignment-field { display: grid; gap: .5rem; min-width: 0; }
    label { font-size: 12px; font-weight: 600; color: var(--muted); }
    select { width: 100%; min-height: 40px; padding: .5rem .6rem; border: 1px solid var(--border); border-radius: 6px; background: white; color: var(--text); font-size: 12px; }
    .button { font-size: 12px; }
    button:disabled { opacity: .5; }
    p { color: #a13636; font-size: .875rem; }
  `,
})
export class TicketAssignment {
  readonly ticket = input.required<Ticket>();
  readonly disabled = input(false);
  readonly busy = model(false);
  readonly saved = output<Ticket>();
  private readonly http = inject(HttpClient);
  private readonly tickets = inject(TicketsService);
  protected readonly error = signal<string | null>(null);
  protected readonly users = resource({ loader: () => firstValueFrom(this.http.get<CurrentUser[]>(`${API_URL}/users`)), defaultValue: [] });
  protected readonly agents = computed(() => this.users.hasValue() ? this.users.value().filter(person => person.role !== 'employee') : []);

  protected save(event: Event): void {
    event.preventDefault();
    if (this.disabled() || this.busy() || this.users.isLoading()) return;
    const value = new FormData(event.target as HTMLFormElement).get('assignee_id');
    this.busy.set(true);
    this.error.set(null);
    this.tickets.assign(this.ticket().id, value ? Number(value) : null, this.ticket().version).subscribe({
      next: (ticket) => { this.busy.set(false); this.saved.emit(ticket); },
      error: (error: unknown) => {
        this.busy.set(false);
        this.error.set(errorMessageFor(error, { 409: 'Die Zuweisung passt nicht mehr zum aktuellen Stand. Bitte Dialog schließen und die Ticketübersicht aktualisieren.', 404: 'Ticket oder Bearbeiter nicht mehr vorhanden.', 422: 'Diese Person darf keine Tickets bearbeiten.' }, 'Zuweisung konnte nicht gespeichert werden.'));
      },
    });
  }
}
