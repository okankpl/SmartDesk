import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { TicketsService } from '../../core/tickets/tickets';
import { TicketPriority } from '../../core/tickets/ticket';

const PRIORITY_OPTIONS: { value: TicketPriority; label: string }[] = [
  { value: 'low', label: 'Niedrig' },
  { value: 'medium', label: 'Mittel' },
  { value: 'high', label: 'Hoch' },
  { value: 'critical', label: 'Kritisch' },
];

@Component({
  selector: 'app-ticket-create',
  imports: [RouterLink],
  templateUrl: './ticket-create.html',
  styleUrl: './ticket-create.scss',
})
export class TicketCreate {
  private readonly ticketsService = inject(TicketsService);
  private readonly router = inject(Router);

  protected readonly priorityOptions = PRIORITY_OPTIONS;

  protected readonly title = signal('');
  protected readonly description = signal('');
  protected readonly priority = signal<TicketPriority>('medium');
  protected readonly errorMessage = signal<string | null>(null);
  protected readonly isSubmitting = signal(false);

  protected onTitleInput(event: Event): void {
    this.title.set((event.target as HTMLInputElement).value);
  }

  protected onDescriptionInput(event: Event): void {
    this.description.set((event.target as HTMLTextAreaElement).value);
  }

  protected onPriorityChange(event: Event): void {
    this.priority.set((event.target as HTMLSelectElement).value as TicketPriority);
  }

  protected submit(event: Event): void {
    event.preventDefault();
    this.errorMessage.set(null);
    this.isSubmitting.set(true);

    const trimmedDescription = this.description().trim();

    this.ticketsService
      .create({
        title: this.title(),
        description: trimmedDescription.length > 0 ? trimmedDescription : null,
        priority: this.priority(),
      })
      .subscribe({
        next: () => {
          this.isSubmitting.set(false);
          // Zurueck zum Dashboard: die dortige resource() laedt beim erneuten
          // Mounten der Komponente automatisch neu (Angular baut Dashboard bei
          // einer Navigation weg und zurueck frisch auf) - kein manuelles
          // "Liste neu laden" noetig.
          this.router.navigateByUrl('/dashboard');
        },
        error: () => {
          this.isSubmitting.set(false);
          this.errorMessage.set('Ticket konnte nicht erstellt werden. Bitte erneut versuchen.');
        },
      });
  }
}
