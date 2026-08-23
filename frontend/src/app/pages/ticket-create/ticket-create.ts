import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { TicketsService } from '../../core/tickets/tickets';
import { TicketPriority } from '../../core/tickets/ticket';

// Feste Liste der Prioritaets-Optionen fuers <select>-Dropdown im Template,
// mit deutscher Beschriftung. "value: TicketPriority" zwingt TypeScript dazu,
// hier nur echte, gueltige Prioritaets-Werte zuzulassen - ein Tippfehler wie
// "meduim" waere ein Compile-Fehler, nicht erst ein Laufzeit-Bug.
const PRIORITY_OPTIONS: { value: TicketPriority; label: string }[] = [
  { value: 'low', label: 'Niedrig' },
  { value: 'medium', label: 'Mittel' },
  { value: 'high', label: 'Hoch' },
  { value: 'critical', label: 'Kritisch' },
];

@Component({
  selector: 'app-ticket-create',
  // RouterLink wird im Template fuer den "Abbrechen"-Link gebraucht
  // (routerLink="/dashboard") - Standalone-Komponenten muessen jede benutzte
  // Direktive/Pipe/Komponente hier explizit auflisten, es gibt kein
  // automatisches "alles verfuegbar" wie frueher bei NgModules.
  imports: [RouterLink],
  templateUrl: './ticket-create.html',
  styleUrl: './ticket-create.scss',
})
export class TicketCreate {
  private readonly ticketsService = inject(TicketsService);
  private readonly router = inject(Router);

  // Wird im Template per @for durchlaufen, um die <option>-Elemente zu erzeugen.
  protected readonly priorityOptions = PRIORITY_OPTIONS;

  // Lokaler Formular-Zustand als Signals, wie schon bei login.ts - kein
  // FormsModule noetig.
  protected readonly title = signal('');
  protected readonly description = signal('');
  // signal<TicketPriority>('medium'): der generische Typ-Parameter <...> legt
  // fest, dass dieses Signal NUR eine der vier TicketPriority-Werte enthalten
  // darf, nicht irgendeinen beliebigen String - 'medium' als Startwert.
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
    // "as HTMLSelectElement" behandelt event.target als <select>-Element (nur
    // dort gibt es .value fuer den aktuell ausgewaehlten <option>-Wert).
    // Zusaetzlich "as TicketPriority", weil TypeScript bei .value nur "string"
    // wissen kann (jedes <select> liefert rohe Strings) - wir behaupten hier,
    // dass dieser String garantiert einer der vier gueltigen Werte ist, weil
    // die <option>-Werte im Template ja exakt aus PRIORITY_OPTIONS stammen.
    this.priority.set((event.target as HTMLSelectElement).value as TicketPriority);
  }

  protected submit(event: Event): void {
    event.preventDefault();
    this.errorMessage.set(null);
    this.isSubmitting.set(true);

    // Eine leere/nur-Leerzeichen-Beschreibung soll als "keine Beschreibung"
    // (null) gelten, nicht als leerer String - .trim() entfernt Leerzeichen
    // am Anfang/Ende, .length prueft danach, ob ueberhaupt noch Text uebrig ist.
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
