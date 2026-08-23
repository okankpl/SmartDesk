// ElementRef ist ein duenner Wrapper um ein echtes DOM-Element (.nativeElement
// gibt das rohe HTMLElement frei) - man braucht ihn, um ausnahmsweise direkt
// mit dem DOM zu arbeiten (hier: showModal()/close() auf einem <dialog>
// aufrufen), statt alles rein deklarativ ueber Bindings zu steuern.
// viewChild() liest eine mit #name im Template markierte Stelle aus (siehe
// #detailDialog in ticket-card.html) - das Angular-Gegenstueck zu
// document.querySelector(...), nur reaktiv und typsicher.
import { Component, ElementRef, computed, input, viewChild } from '@angular/core';
// DatePipe ist die Klasse hinter dem "| date"-Pipe-Syntax im Template
// (siehe ticket-card.html) - Pipes muessen wie Komponenten/Direktiven im
// "imports"-Array der Standalone-Komponente aufgefuehrt werden.
import { DatePipe } from '@angular/common';
import { Ticket, TicketPriority, TicketStatus } from '../../../core/tickets/ticket';

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

@Component({
  selector: 'app-ticket-card',
  imports: [DatePipe],
  templateUrl: './ticket-card.html',
  styleUrl: './ticket-card.scss'
})
export class TicketCard {
  // input.required<Ticket>() erklaert eine PFLICHT-Eingabe: die Elternkomponente
  // (Dashboard, per [ticket]="ticket" in dashboard.html) MUSS ein Ticket
  // reinreichen, sonst meldet Angular schon beim Kompilieren einen Fehler.
  // ticket() liest den aktuellen Wert - Inputs sind seit neueren
  // Angular-Versionen selbst Signals, aendert sich der uebergebene Wert,
  // reagieren alle computed()s unten automatisch darauf.
  readonly ticket = input.required<Ticket>();

  // Beschriftung für das Status-Badge, abgeleitet aus dem aktuellen Ticket-Status.
  protected readonly statusLabel = computed(() => STATUS_LABELS[this.ticket().status]);

  // Beschriftung für das Prioritäts-Badge, abgeleitet aus der aktuellen Priorität.
  protected readonly priorityLabel = computed(() => PRIORITY_LABELS[this.ticket().priority]);

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

  // showModal() ist eine eingebaute Methode JEDES <dialog>-Elements (kein
  // Angular-spezifisches API) - macht es sichtbar UND modal (Rest der Seite
  // per Tab-Taste nicht mehr erreichbar, ::backdrop erscheint automatisch).
  protected openDetails(): void {
    this.dialog().nativeElement.showModal();
  }

  // close() ist das Gegenstueck zu showModal() - blendet den Dialog wieder
  // aus und gibt die Bedienung des Rests der Seite frei.
  protected closeDetails(): void {
    this.dialog().nativeElement.close();
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
}
