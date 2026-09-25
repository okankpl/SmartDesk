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
import { Component, ElementRef, computed, inject, input, output, signal, viewChild } from '@angular/core';
// DatePipe ist die Klasse hinter dem "| date"-Pipe-Syntax im Template
// (siehe ticket-card.html) - Pipes muessen wie Komponenten/Direktiven im
// "imports"-Array der Standalone-Komponente aufgefuehrt werden.
import { DatePipe } from '@angular/common';
import { TicketsService } from '../../../core/tickets/tickets';
import { Ticket, TicketPriority, TicketStatus } from '../../../core/tickets/ticket';
import { TicketComments } from '../ticket-comments/ticket-comments';

// Record<TicketStatus, string> ist ein TypeScript-Utility-Type: "ein Objekt,
// das fuer JEDEN moeglichen TicketStatus-Wert einen String-Eintrag hat, nicht
// mehr und nicht weniger". Vergisst man hier einen der vier Status, meldet
// der Compiler sofort einen Fehler - eine simple Record<string, string>
// wuerde das nicht garantieren.
//
// Deutsche Beschriftung für jeden Ticket-Status im Status-Badge.
const STATUS_LABELS: Record<TicketStatus, string> = {
  open: 'Offen',
  in_progress: 'In Bearbeitung',
  resolved: 'Gelöst',
  closed: 'Geschlossen',
};

// Deutsche Beschriftung für jede Priorität im Prioritäts-Badge.
const PRIORITY_LABELS: Record<TicketPriority, string> = {
  low: 'Niedrig',
  medium: 'Mittel',
  high: 'Hoch',
  critical: 'Kritisch',
};

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
  imports: [DatePipe, TicketComments],
  templateUrl: './ticket-card.html',
  styleUrl: './ticket-card.scss'
})
export class TicketCard {
  private readonly ticketsService = inject(TicketsService);

  // input.required<Ticket>() erklaert eine PFLICHT-Eingabe: die Elternkomponente
  // (Dashboard, per [ticket]="ticket" in dashboard.html) MUSS ein Ticket
  // reinreichen, sonst meldet Angular schon beim Kompilieren einen Fehler.
  // ticket() liest den aktuellen Wert - Inputs sind seit neueren
  // Angular-Versionen selbst Signals, aendert sich der uebergebene Wert,
  // reagieren alle computed()s unten automatisch darauf.
  readonly ticket = input.required<Ticket>();

  // Feuert, nachdem ein Statuswechsel erfolgreich war - Dashboard reagiert
  // darauf, indem es die Ticketliste neu laedt (siehe dashboard.html). Diese
  // Komponente kennt die Gesamtliste gar nicht, deshalb kann/soll sie sie
  // nicht selbst neu laden - sie meldet nur "bei mir hat sich was getan"
  // nach oben (unidirektionaler Datenfluss: Daten fliessen von Dashboard
  // runter zu TicketCard per Input, Ereignisse fliessen per Output wieder hoch).
  readonly statusChanged = output<void>();

  // Beschriftung für das Status-Badge, abgeleitet aus dem aktuellen Ticket-Status.
  protected readonly statusLabel = computed(() => STATUS_LABELS[this.ticket().status]);

  // Beschriftung für das Prioritäts-Badge, abgeleitet aus der aktuellen Priorität.
  protected readonly priorityLabel = computed(() => PRIORITY_LABELS[this.ticket().priority]);

  // Baut aus ticket().allowed_transitions (vom Backend berechnet, siehe
  // ticket.ts) die anzuzeigenden Buttons: pro erlaubtem Ziel-Status ein
  // {status, label}-Paar. Zeigt NIE einen Button fuer einen Uebergang, den
  // der aktuelle Nutzer laut Backend gerade nicht ausloesen duerfte.
  protected readonly availableActions = computed(() => {
    const currentTicket = this.ticket();
    const labelsForCurrentStatus = TRANSITION_ACTION_LABELS[currentTicket.status];
    return currentTicket.allowed_transitions.map((targetStatus) => ({
      targetStatus,
      label: labelsForCurrentStatus[targetStatus] ?? STATUS_LABELS[targetStatus],
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
    this.statusChangeError.set(null);
    this.isDetailOpen.set(true);
    this.dialog().nativeElement.showModal();
  }

  // close() ist das Gegenstueck zu showModal() - blendet den Dialog wieder
  // aus und gibt die Bedienung des Rests der Seite frei.
  protected closeDetails(): void {
    this.dialog().nativeElement.close();
  }

  // Wird ueber (close)="onDialogClosed()" im Template aufgerufen. Das native
  // "close"-Event feuert bei JEDER Art des Schliessens - ueber closeDetails()
  // (X-Button, Klick daneben, nach Statuswechsel) UND ueber die Escape-Taste,
  // die der Browser selbst behandelt, ohne dass unser Code davon etwas
  // mitbekaeme. Deshalb wird isDetailOpen HIER zurueckgesetzt und nicht in
  // closeDetails() - sonst wuerde "mit Escape geschlossen" als "noch offen"
  // gelten, TicketComments bliebe bestehen und wuerde beim naechsten Oeffnen
  // nicht frisch laden.
  protected onDialogClosed(): void {
    this.isDetailOpen.set(false);
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
    this.isChangingStatus.set(true);
    this.statusChangeError.set(null);

    this.ticketsService.updateStatus(this.ticket().id, targetStatus).subscribe({
      next: () => {
        this.isChangingStatus.set(false);
        // Der Dialog zeigt sonst weiter den ALTEN Status/die alten Buttons an,
        // bis Dashboard neu geladen hat und diese Komponente mit einem neuen
        // ticket()-Wert neu aufgebaut wird - einfacher, ihn direkt zu schliessen.
        this.closeDetails();
        this.statusChanged.emit();
      },
      error: () => {
        // z.B. 409, wenn zwischenzeitlich schon jemand anders den Status
        // geaendert hat (Wettlaufsituation) - dem Nutzer eine verstaendliche
        // Meldung zeigen statt den Fehler stillschweigend zu verschlucken.
        this.isChangingStatus.set(false);
        this.statusChangeError.set('Aktion nicht möglich. Vielleicht wurde das Ticket gerade geändert - Seite neu laden.');
      },
    });
  }
}
