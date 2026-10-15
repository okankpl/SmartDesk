// ElementRef ist ein duenner Wrapper um ein echtes DOM-Element (.nativeElement
// gibt das rohe HTMLElement frei) - man braucht ihn, um ausnahmsweise direkt
// mit dem DOM zu arbeiten (hier: showModal()/close() auf einem <dialog>
// aufrufen), statt alles rein deklarativ ueber Bindings zu steuern.
// viewChild() liest eine mit #name im Template markierte Stelle aus (siehe
// #detailDialog in ticket-card.html) - das Angular-Gegenstueck zu
// document.querySelector(...), nur reaktiv und typsicher. output() erzeugt
// ein Signal-basiertes Event, das die Elternkomponente (Dashboard) per
// (statusChanged)="..." abonnieren kann - das Angular-Gegenstueck zum
// aelteren @Output() EventEmitter, nur ohne Decorator/Klasse.
import { Component, ElementRef, Injector, afterNextRender, computed, inject, input, output, signal, viewChild } from '@angular/core';
// DatePipe ist die Klasse hinter dem "| date"-Pipe-Syntax im Template
// (siehe ticket-card.html) - Pipes muessen wie Komponenten/Direktiven im
// "imports"-Array der Standalone-Komponente aufgefuehrt werden.
import { DatePipe } from '@angular/common';
import { LucideX, LucideCheck, LucideLockKeyhole, LucideRotateCcw, LucidePlay, LucideDynamicIcon, LucideCircleCheck, LucidePencil, LucideSave } from '@lucide/angular';
import { errorMessageFor } from '../../../core/http-error-message';
import { TicketsService } from '../../../core/tickets/tickets';
import { Ticket, TicketStatus } from '../../../core/tickets/ticket';
import { TicketComments } from '../ticket-comments/ticket-comments';
import { TicketHistory } from '../ticket-history/ticket-history';
import { TicketAssignment } from '../ticket-assignment/ticket-assignment';
import { Auth } from '../../../core/auth/auth';
import { STATUS_LABELS, PRIORITY_LABELS } from '../../../core/tickets/ticket-labels';
import { TicketPreview } from '../ticket-preview/ticket-preview';
import { TicketEditor } from '../ticket-editor/ticket-editor';

// Beschriftung fuer die Aktions-Buttons im Detail-Popup - verschachtelt nach
// AKTUELLEM Status, weil derselbe Ziel-Status je nach Ausgangslage eine andere
// Bedeutung hat: IN_PROGRESS ist von OPEN aus gesehen ein "Übernehmen", von
// RESOLVED aus gesehen dagegen ein "Ablehnen" (siehe ALLOWED_TRANSITIONS in
// ticket_lifecycle.py, das ist genau dieselbe Struktur). "Partial<...>", weil
// nicht jeder Status ein Ziel fuer jeden Ausgangsstatus hat (CLOSED hat z.B.
// gar keine Eintraege).
const TRANSITION_ACTION_LABELS: Record<TicketStatus, Partial<Record<TicketStatus, string>>> = {
  open: { in_progress: 'Übernehmen' },
  in_progress: { resolved: 'Als gelöst markieren' },
  resolved: { closed: 'Schließen', in_progress: 'Ablehnen' },
  closed: {},
};

@Component({
  selector: 'app-ticket-card',
  imports: [DatePipe, TicketComments, TicketHistory, TicketAssignment, TicketPreview, TicketEditor, LucideX, LucideDynamicIcon, LucideCircleCheck, LucidePencil, LucideSave],
  templateUrl: './ticket-card.html',
  styleUrl: './ticket-card.scss'
})
export class TicketCard {
  private readonly ticketsService = inject(TicketsService);
  private readonly injector = inject(Injector);
  protected readonly currentUser = inject(Auth).currentUser;

  // input.required<Ticket>() erklaert eine PFLICHT-Eingabe: die Elternkomponente
  // (Dashboard, per [ticket]="ticket" in dashboard.html) MUSS ein Ticket
  // reinreichen, sonst meldet Angular schon beim Kompilieren einen Fehler.
  // ticket() liest den aktuellen Wert - Inputs sind seit neueren
  // Angular-Versionen selbst Signals, aendert sich der uebergebene Wert,
  // reagieren alle computed()s unten automatisch darauf.
  readonly ticket = input.required<Ticket>();
  readonly compact = input(false);
  readonly highlighted = input(false);
  private readonly updatedTicket = signal<Ticket | null>(null);
  protected readonly detailTicket = computed(() => this.updatedTicket() ?? this.ticket());
  protected readonly historyRevision = signal(0);
  protected readonly successMessage = signal<string | null>(null);
  protected readonly isEditing = signal(false);
  protected readonly isAssigning = signal(false);
  protected readonly confirmDiscard = signal(false);
  private closeAfterDiscard = false;
  protected readonly editor = viewChild(TicketEditor);
  private readonly editButton = viewChild<ElementRef<HTMLButtonElement>>('editButton');
  protected readonly canEdit = computed(() => ['agent', 'admin'].includes(this.currentUser()?.role ?? '') && this.detailTicket().status !== 'closed');
  protected readonly isBusy = computed(() => this.isChangingStatus() || this.isAssigning() || !!this.editor()?.busy());
  private hasChanges = false;

  // Confirmed changes refresh the parent queue after the dialog closes.
  readonly statusChanged = output<void>();

  // Beschriftung für das Status-Badge, abgeleitet aus dem aktuellen Ticket-Status.
  protected readonly statusLabel = computed(() => STATUS_LABELS[this.detailTicket().status]);

  // Beschriftung für das Prioritäts-Badge, abgeleitet aus der aktuellen Priorität.
  protected readonly priorityLabel = computed(() => PRIORITY_LABELS[this.detailTicket().priority]);

  // Baut aus ticket().allowed_transitions (vom Backend berechnet, siehe
  // ticket.ts) die anzuzeigenden Buttons: pro erlaubtem Ziel-Status ein
  // {status, label}-Paar. Zeigt NIE einen Button fuer einen Uebergang, den
  // der aktuelle Nutzer laut Backend gerade nicht ausloesen duerfte.
  protected readonly availableActions = computed(() => {
    const currentTicket = this.detailTicket();
    const labelsForCurrentStatus = TRANSITION_ACTION_LABELS[currentTicket.status];
    return currentTicket.allowed_transitions.map((targetStatus) => ({
      targetStatus,
      label: labelsForCurrentStatus[targetStatus] ?? STATUS_LABELS[targetStatus],
      icon: targetStatus === 'closed' ? LucideLockKeyhole : targetStatus === 'resolved' ? LucideCheck : currentTicket.status === 'resolved' ? LucideRotateCcw : LucidePlay,
    }));
  });

  protected readonly isChangingStatus = signal(false);
  protected readonly statusChangeError = signal<string | null>(null);

  // Referenz auf das native <dialog>-Element im Template. Ein <dialog> bringt
  // Fokus-Handling, Escape-zum-Schließen und den Hintergrund-Abdunkler
  // (::backdrop) bereits eingebaut mit - kein eigenes Overlay/Fokus-Trap
  // noetig, wie es eine selbstgebaute Modal-Loesung bräuchte.
  //
  // viewChild.required(...) statt viewChild(...): "required" sagt, dass
  // #detailDialog im Template garantiert existiert (kein @if drumherum, das
  // es manchmal verschwinden liesse) - dialog() gibt dann direkt das Element
  // zurueck statt eines "Element-oder-undefined"-Typs, den man jedes Mal
  // pruefen muesste.
  private readonly dialog = viewChild.required<ElementRef<HTMLDialogElement>>('detailDialog');
  private readonly detailBody = viewChild<ElementRef<HTMLDivElement>>('detailBody');

  // Ist das Detail-Popup gerade offen? Steuert im Template per @if, ob der
  // Kommentarbereich (<app-ticket-comments>) ueberhaupt existiert.
  //
  // Warum der Aufwand? Das Dashboard erzeugt fuer JEDES Ticket eine eigene
  // TicketCard. Wuerde jede Karte ihren Kommentarbereich (und damit dessen
  // GET-Anfrage) sofort mit erzeugen, gingen bei 30 Tickets 30 Anfragen an den
  // Server - obwohl der Nutzer vielleicht kein einziges Popup oeffnet. So
  // entsteht TicketComments erst beim Oeffnen und laedt erst dann ("Lazy
  // Loading", bedarfsgesteuertes Nachladen).
  protected readonly isDetailOpen = signal(false);

  // showModal() ist eine eingebaute Methode JEDES <dialog>-Elements (kein
  // Angular-spezifisches API) - macht es sichtbar UND modal (Rest der Seite
  // per Tab-Taste nicht mehr erreichbar, ::backdrop erscheint automatisch).
  protected openDetails(): void {
    this.updatedTicket.set(null);
    this.successMessage.set(null);
    this.hasChanges = false;
    this.statusChangeError.set(null);
    this.isEditing.set(false);
    this.confirmDiscard.set(false);
    this.isDetailOpen.set(true);
    this.dialog().nativeElement.showModal();
    if (this.detailBody()) this.detailBody()!.nativeElement.scrollTop = 0;
  }

  // close() ist das Gegenstueck zu showModal() - blendet den Dialog wieder
  // aus und gibt die Bedienung des Rests der Seite frei.
  protected closeDetails(): void {
    if (this.isBusy()) return;
    if (this.isEditing() && this.editor()?.dirty()) {
      this.closeAfterDiscard = true;
      this.confirmDiscard.set(true);
      return;
    }
    this.dialog().nativeElement.close();
  }

  protected beginEditing(): void {
    if (!this.canEdit() || this.isBusy()) return;
    this.successMessage.set(null);
    this.statusChangeError.set(null);
    this.confirmDiscard.set(false);
    this.isEditing.set(true);
    if (this.detailBody()) this.detailBody()!.nativeElement.scrollTop = 0;
  }

  protected cancelEditing(): void {
    if (this.isBusy()) return;
    if (this.editor()?.dirty()) {
      this.closeAfterDiscard = false;
      this.confirmDiscard.set(true);
    } else {
      this.finishEditing();
    }
  }

  protected discardEditing(): void {
    if (this.isBusy()) return;
    this.finishEditing(!this.closeAfterDiscard);
    if (this.closeAfterDiscard) this.dialog().nativeElement.close();
  }

  protected continueEditing(): void {
    this.confirmDiscard.set(false);
    afterNextRender(() => this.dialog().nativeElement.querySelector<HTMLInputElement>('app-ticket-editor input')?.focus(), { injector: this.injector });
  }

  private finishEditing(restoreFocus = true): void {
    this.isEditing.set(false);
    this.confirmDiscard.set(false);
    if (restoreFocus) afterNextRender(() => this.editButton()?.nativeElement.focus(), { injector: this.injector });
  }

  protected onContentSaved(ticket: Ticket): void {
    this.acceptUpdate(ticket, 'Ticketänderungen wurden gespeichert.');
    this.finishEditing();
  }

  protected onContentReloaded(ticket: Ticket): void {
    this.acceptUpdate(ticket, ticket.status === 'closed' ? 'Der aktuelle Stand wurde geladen. Das Ticket ist geschlossen.' : 'Der aktuelle Stand wurde geladen.');
    if (ticket.status === 'closed') this.finishEditing();
  }

  protected onAssignmentSaved(ticket: Ticket): void {
    this.acceptUpdate(ticket, 'Bearbeiter wurde aktualisiert.');
  }

  private acceptUpdate(ticket: Ticket, message: string): void {
    this.updatedTicket.set(ticket);
    this.successMessage.set(message);
    this.historyRevision.update(value => value + 1);
    this.hasChanges = true;
    if (!this.isDetailOpen()) {
      this.hasChanges = false;
      this.statusChanged.emit();
    }
  }

  protected onDialogCancel(event: Event): void {
    if (this.isBusy() || this.isEditing()) {
      event.preventDefault();
      this.closeDetails();
    }
  }

  // Wird ueber (close)="onDialogClosed()" im Template aufgerufen. Das native
  // "close"-Event feuert bei JEDER Art des Schliessens - ueber closeDetails()
  // (X-Button oder Klick daneben) UND ueber die Escape-Taste,
  // die der Browser selbst behandelt, ohne dass unser Code davon etwas
  // mitbekaeme. Deshalb wird isDetailOpen HIER zurueckgesetzt und nicht in
  // closeDetails() - sonst wuerde "mit Escape geschlossen" als "noch offen"
  // gelten, TicketComments bliebe bestehen und wuerde beim naechsten Oeffnen
  // nicht frisch laden.
  protected onDialogClosed(): void {
    this.isDetailOpen.set(false);
    this.isEditing.set(false);
    this.confirmDiscard.set(false);
    // Refresh after closing, so a moved ticket cannot destroy its open dialog.
    if (this.hasChanges) {
      this.hasChanges = false;
      this.statusChanged.emit();
    }
  }

  // showModal() macht das <dialog> zwar modal, "Klick daneben schliessen" ist
  // aber kein eingebautes Verhalten - ein Klick auf den Dialog selbst (statt
  // auf ein Kind-Element darin) bedeutet "auf den Backdrop-Bereich geklickt".
  // event.target ist bei einem Klick immer das TATSAECHLICH angeklickte
  // Element - klickt man auf die Beschreibung INNERHALB des Dialogs, ist
  // target dieses innere Element, nicht das <dialog> selbst, deshalb schliesst
  // dieser Handler den Dialog dann nicht versehentlich.
  protected onBackdropClick(event: MouseEvent): void {
    if (event.target === this.dialog().nativeElement) {
      this.closeDetails();
    }
  }

  // Wird per (click) auf einen der Aktions-Buttons ausgeloest.
  protected changeStatus(targetStatus: TicketStatus): void {
    if (this.isBusy() || this.isEditing()) return;
    this.isChangingStatus.set(true);
    this.statusChangeError.set(null);

    this.ticketsService.updateStatus(this.ticket().id, targetStatus).subscribe({
      next: (ticket) => {
        this.isChangingStatus.set(false);
        this.acceptUpdate(ticket, 'Status geändert: ' + STATUS_LABELS[ticket.status] + '.');
      },
      error: (error: unknown) => {
        // 409, wenn zwischenzeitlich schon jemand anders den Status
        // geaendert hat (Wettlaufsituation), 403/404 bei fehlender
        // Berechtigung bzw. geloeschtem Ticket - dem Nutzer jeweils eine
        // verstaendliche Meldung zeigen statt den Fehler zu verschlucken.
        this.isChangingStatus.set(false);
        this.statusChangeError.set(
          errorMessageFor(
            error,
            {
              403: 'Für diese Aktion fehlt dir die Berechtigung.',
              404: 'Dieses Ticket gibt es nicht mehr. Bitte Seite neu laden.',
              409: 'Das Ticket wurde inzwischen geändert. Bitte Seite neu laden.',
            },
            'Aktion nicht möglich. Bitte erneut versuchen.',
          ),
        );
      },
    });
  }
}
