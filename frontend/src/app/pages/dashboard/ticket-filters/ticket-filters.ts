import { Component, input, model } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { LucideSearch, LucideX } from '@lucide/angular';
import { TicketPriority } from '../../../core/tickets/ticket';

export type SortOrder = 'priority' | 'oldest' | 'newest';

@Component({
  selector: 'app-ticket-filters',
  imports: [FormsModule, LucideSearch, LucideX],
  templateUrl: './ticket-filters.html',
  styleUrl: './ticket-filters.scss',
})
export class TicketFilters {
  readonly support = input(false);
  readonly search = model('');
  readonly priority = model<TicketPriority | ''>('');
  readonly assignment = model<'all' | 'mine' | 'unassigned'>('all');
  readonly sort = model<SortOrder>('priority');
}
