import { Component, ElementRef, afterNextRender, computed, inject, input, linkedSignal, output, signal, viewChild } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { LucideRefreshCw } from '@lucide/angular';
import { Ticket, TicketPriority } from '../../../core/tickets/ticket';
import { TicketContentUpdate, TicketsService } from '../../../core/tickets/tickets';
import { PRIORITY_LABELS } from '../../../core/tickets/ticket-labels';
import { errorMessageFor } from '../../../core/http-error-message';

@Component({
  selector: 'app-ticket-editor',
  imports: [FormsModule, LucideRefreshCw],
  templateUrl: './ticket-editor.html',
  styleUrl: './ticket-editor.scss',
})
export class TicketEditor {
  readonly ticket = input.required<Ticket>();
  readonly saved = output<Ticket>();
  readonly reloaded = output<Ticket>();
  readonly formId = computed(() => `ticket-edit-${this.ticket().id}`);
  private readonly tickets = inject(TicketsService);
  private readonly titleInput = viewChild.required<ElementRef<HTMLInputElement>>('titleInput');
  protected readonly title = linkedSignal(() => this.ticket().title);
  protected readonly description = linkedSignal(() => this.ticket().description ?? '');
  protected readonly priority = linkedSignal(() => this.ticket().priority);
  protected readonly priorityOptions = Object.entries(PRIORITY_LABELS) as [TicketPriority, string][];
  protected readonly titleError = signal<string | null>(null);
  protected readonly descriptionError = signal<string | null>(null);
  protected readonly error = signal<string | null>(null);
  readonly conflict = signal(false);
  readonly saving = signal(false);
  private readonly loading = signal(false);
  readonly busy = computed(() => this.saving() || this.loading());
  private readonly changes = computed(() => {
    const current = this.ticket();
    const changes: TicketContentUpdate = { expected_version: current.version };
    if (this.title().trim() !== current.title) changes.title = this.title().trim();
    const description = this.description().trim() || null;
    if (description !== (current.description?.trim() || null)) changes.description = description;
    if (this.priority() !== current.priority) changes.priority = this.priority();
    return changes;
  });
  readonly dirty = computed(() => Object.keys(this.changes()).length > 1);

  constructor() {
    afterNextRender(() => this.titleInput().nativeElement.focus());
  }

  protected submit(event: Event): void {
    event.preventDefault();
    if (this.busy() || this.conflict()) return;
    const form = event.target as HTMLFormElement;
    this.titleError.set(!this.title().trim() ? 'Bitte einen Titel eingeben.' : this.title().trim().length > 200 ? 'Der Titel darf höchstens 200 Zeichen enthalten.' : null);
    this.descriptionError.set(this.description().length > 10_000 ? 'Die Beschreibung darf höchstens 10.000 Zeichen enthalten.' : null);
    if (this.titleError()) { this.titleInput().nativeElement.focus(); return; }
    if (this.descriptionError() || !form.reportValidity() || !this.dirty()) return;
    this.error.set(null);
    this.saving.set(true);
    this.tickets.updateContent(this.ticket().id, this.changes()).subscribe({
      next: ticket => { this.saving.set(false); this.saved.emit(ticket); },
      error: (error: unknown) => {
        this.saving.set(false);
        this.conflict.set(error instanceof HttpErrorResponse && error.status === 409);
        this.error.set(errorMessageFor(error, {
          403: 'Du darfst dieses Ticket nicht bearbeiten.',
          404: 'Dieses Ticket ist nicht mehr verfügbar.',
          409: 'Das Ticket wurde inzwischen geändert oder geschlossen. Dein Entwurf wurde nicht gespeichert.',
          422: 'Bitte Eingaben prüfen: Titel höchstens 200, Beschreibung höchstens 10.000 Zeichen.',
        }, 'Änderungen konnten nicht gespeichert werden. Bitte erneut versuchen.'));
      },
    });
  }

  protected reload(): void {
    if (this.busy()) return;
    this.loading.set(true);
    this.tickets.get(this.ticket().id).subscribe({
      next: ticket => {
        this.loading.set(false);
        this.error.set(null);
        this.conflict.set(false);
        this.titleError.set(null);
        this.descriptionError.set(null);
        this.reloaded.emit(ticket);
      },
      error: (error: unknown) => {
        this.loading.set(false);
        this.error.set(errorMessageFor(error, { 404: 'Dieses Ticket ist nicht mehr verfügbar.' }, 'Der aktuelle Stand konnte nicht geladen werden. Dein Entwurf bleibt erhalten.'));
      },
    });
  }
}
