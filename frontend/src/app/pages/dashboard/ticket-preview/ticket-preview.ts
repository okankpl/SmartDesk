import { Component, computed, input, output } from '@angular/core';
import { DatePipe } from '@angular/common';
import { LucideUserRound, LucideArrowUpRight } from '@lucide/angular';
import { Ticket } from '../../../core/tickets/ticket';
import { STATUS_LABELS, PRIORITY_LABELS } from '../../../core/tickets/ticket-labels';

@Component({
  selector: 'app-ticket-preview',
  imports: [DatePipe, LucideUserRound, LucideArrowUpRight],
  templateUrl: './ticket-preview.html',
  styleUrl: './ticket-preview.scss',
})
export class TicketPreview {
  readonly ticket = input.required<Ticket>();
  readonly compact = input(false);
  readonly highlighted = input(false);
  readonly openTicket = output<void>();
  protected readonly statusLabel = computed(() => STATUS_LABELS[this.ticket().status]);
  protected readonly priorityLabel = computed(() => PRIORITY_LABELS[this.ticket().priority]);
}
