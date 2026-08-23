import { Component, ElementRef, computed, input, viewChild } from '@angular/core';
import { DatePipe } from '@angular/common';
import { Ticket, TicketPriority, TicketStatus } from '../../../core/tickets/ticket';

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
  readonly ticket = input.required<Ticket>();

  // Beschriftung für das Status-Badge, abgeleitet aus dem aktuellen Ticket-Status.
  protected readonly statusLabel = computed(() => STATUS_LABELS[this.ticket().status]);

  // Beschriftung für das Prioritäts-Badge, abgeleitet aus der aktuellen Priorität.
  protected readonly priorityLabel = computed(() => PRIORITY_LABELS[this.ticket().priority]);

  // Referenz auf das native <dialog>-Element im Template. Ein <dialog> bringt
  // Fokus-Handling, Escape-zum-Schließen und den Hintergrund-Abdunkler
  // (::backdrop) bereits eingebaut mit - kein eigenes Overlay/Fokus-Trap
  // noetig, wie es eine selbstgebaute Modal-Loesung bräuchte.
  private readonly dialog = viewChild.required<ElementRef<HTMLDialogElement>>('detailDialog');

  protected openDetails(): void {
    this.dialog().nativeElement.showModal();
  }

  protected closeDetails(): void {
    this.dialog().nativeElement.close();
  }

  // showModal() macht das <dialog> zwar modal, "Klick daneben schliessen" ist
  // aber kein eingebautes Verhalten - ein Klick auf den Dialog selbst (statt
  // auf ein Kind-Element darin) bedeutet "auf den Backdrop-Bereich geklickt".
  protected onBackdropClick(event: MouseEvent): void {
    if (event.target === this.dialog().nativeElement) {
      this.closeDetails();
    }
  }
}
