// resource() ist dieselbe API fuer asynchron geladene Daten wie im Dashboard
// (siehe ausfuehrliche Erklaerung in dashboard.ts).
import { Component, computed, inject, input, resource, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
// firstValueFrom wandelt ein Observable (HttpClient) in ein Promise um, weil
// der "loader" von resource() ein Promise erwartet - wie in dashboard.ts.
import { firstValueFrom } from 'rxjs';

import { Auth } from '../../../core/auth/auth';
import { CommentsService } from '../../../core/comments/comments';
import { TicketComment } from '../../../core/comments/comment';

// Kommentarverlauf + Eingabeformular zu EINEM Ticket. Eigene Komponente statt
// Teil von TicketCard, weil TicketCard schon Karte, Detail-Popup und
// Statuswechsel verantwortet - der Kommentarbereich ist ein eigenstaendiger
// Baustein mit eigenem Zustand (Liste, Laden, Fehler, Formular) und eigenen
// Tests (Single Responsibility Principle: eine Komponente, eine Aufgabe).
//
// Wird von TicketCard NUR gerendert, solange das Detail-Popup offen ist (siehe
// @if in ticket-card.html). Dadurch gilt: Komponente wird erzeugt = Popup geht
// auf = Kommentare werden geladen; Komponente wird zerstoert = Popup geht zu =
// aller Zustand (Liste, Fehlermeldungen, halb getippter Text) ist weg. Beim
// naechsten Oeffnen startet alles frisch und man sieht auch neue Kommentare
// anderer.
@Component({
  selector: 'app-ticket-comments',
  imports: [DatePipe],
  templateUrl: './ticket-comments.html',
  styleUrl: './ticket-comments.scss',
})
export class TicketComments {
  private readonly commentsService = inject(CommentsService);
  private readonly auth = inject(Auth);

  // Nur die ID, nicht das ganze Ticket - mehr braucht diese Komponente nicht.
  // Je weniger eine Komponente von aussen verlangt, desto einfacher ist sie
  // zu testen und an anderer Stelle wiederzuverwenden.
  readonly ticketId = input.required<number>();

  // "params" ist die Eingabe fuer den loader: resource() ruft params() auf und
  // fuehrt den loader automatisch aus - beim Erzeugen der Komponente und
  // erneut, falls sich ticketId() jemals aendern sollte.
  // ({ params: ticketId }) ist "Destructuring": aus dem Objekt, das resource()
  // dem loader uebergibt, wird das Feld "params" herausgezogen und lokal
  // "ticketId" genannt. defaultValue: [] sorgt dafuer, dass value() vor dem
  // ersten Laden ein leeres Array statt undefined ist.
  private readonly commentsResource = resource({
    params: () => this.ticketId(),
    loader: ({ params: ticketId }) => firstValueFrom(this.commentsService.list(ticketId)),
    defaultValue: [],
  });

  // Unter sprechenderen Namen fuers Template weitergereicht, wie in dashboard.ts.
  // ACHTUNG: comments() (= value()) wirft im Fehlerzustand eine Exception -
  // das Template prueft deshalb IMMER zuerst commentsError(), bevor es
  // comments() liest (siehe Reihenfolge der @if-Zweige in ticket-comments.html).
  protected readonly comments = this.commentsResource.value;
  protected readonly isLoadingComments = this.commentsResource.isLoading;
  protected readonly commentsError = this.commentsResource.error;

  // Formular-Zustand fuer einen neuen Kommentar - Signals statt FormsModule,
  // wie schon in login.ts und ticket-create.ts.
  protected readonly newCommentBody = signal('');
  protected readonly isSubmitting = signal(false);
  protected readonly submitError = signal<string | null>(null);

  // Senden-Button nur aktiv, wenn nach Entfernen der Leerzeichen am Rand
  // ueberhaupt Text uebrig ist UND nicht gerade schon gesendet wird (verhindert
  // Doppel-Kommentare durch schnelles Doppelklicken). Das Backend prueft
  // "leer" trotzdem nochmal selbst (CommentCreate, 422) - die Pruefung hier
  // ist nur Komfort fuer den Nutzer, KEINE Sicherheitsmassnahme: ein Angreifer
  // koennte das Frontend jederzeit umgehen und direkt die API aufrufen.
  protected readonly canSubmit = computed(() => this.newCommentBody().trim().length > 0 && !this.isSubmitting());

  // "?." ist Optional Chaining: ist currentUser() null (niemand eingeloggt),
  // bricht der Ausdruck ab und liefert undefined, statt mit "Cannot read
  // properties of null" abzustuerzen - undefined ist dann nie gleich einer
  // author_id, der Kommentar gilt also korrekt als "nicht von mir".
  protected isOwnComment(comment: TicketComment): boolean {
    return comment.author_id === this.auth.currentUser()?.id;
  }

  // Anzeigename des Autors. Das Backend liefert aktuell nur author_id, keinen
  // Namen - fuer eigene Kommentare reicht "Du" (die eigene ID kennt das
  // Frontend aus /auth/me), fuer alle anderen bleibt vorerst nur die Nummer.
  // `...${...}...` (Backticks) ist ein Template-String: ${...} setzt den Wert
  // eines Ausdrucks direkt in den Text ein.
  protected authorLabel(comment: TicketComment): string {
    return this.isOwnComment(comment) ? 'Du' : `Nutzer #${comment.author_id}`;
  }

  protected onBodyInput(event: Event): void {
    this.newCommentBody.set((event.target as HTMLTextAreaElement).value);
  }

  // Wird per (submit) am <form> ausgeloest.
  protected submit(event: Event): void {
    // Ein <form> ohne Angulars FormsModule verhaelt sich wie reines HTML: beim
    // Absenden wuerde der Browser die GANZE Seite neu laden (klassisches
    // Formular-Verhalten aus der Zeit vor Single-Page-Apps). preventDefault()
    // unterdrueckt genau dieses Standardverhalten - wie in ticket-create.ts.
    event.preventDefault();
    this.isSubmitting.set(true);
    this.submitError.set(null);

    this.commentsService.create(this.ticketId(), this.newCommentBody()).subscribe({
      next: (createdComment) => {
        this.isSubmitting.set(false);
        // Textfeld leeren - das Template bindet [value]="newCommentBody()",
        // also leert sich die <textarea> automatisch mit.
        this.newCommentBody.set('');
        // Den vom Server BESTAETIGTEN Kommentar (inkl. echter id und
        // created_at) direkt ans Ende der Liste haengen, statt die komplette
        // Liste neu zu laden - spart eine Anfrage und die Liste flackert nicht
        // kurz auf "wird geladen". update() bekommt die aktuelle Liste und
        // liefert die neue zurueck; [...alt, neu] ist der Spread-Operator:
        // "alle Elemente der alten Liste, dann das neue" - erzeugt ein NEUES
        // Array statt das alte zu veraendern (push() wuerde das alte Array
        // veraendern, und Signals erkennen nur neue Werte als Aenderung).
        this.commentsResource.update((comments) => [...comments, createdComment]);
      },
      error: () => {
        // Eingetippter Text bleibt bewusst stehen, damit er nicht verloren
        // geht und der Nutzer es einfach nochmal versuchen kann.
        this.isSubmitting.set(false);
        this.submitError.set('Kommentar konnte nicht gespeichert werden. Bitte erneut versuchen.');
      },
    });
  }
}
