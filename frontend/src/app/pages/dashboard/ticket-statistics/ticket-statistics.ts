import { Component, input } from '@angular/core';
import { LucideInbox, LucideTriangleAlert, LucideCircleCheck, LucideClock3 } from '@lucide/angular';

@Component({
  selector: 'app-ticket-statistics',
  imports: [LucideInbox, LucideTriangleAlert, LucideCircleCheck, LucideClock3],
  template: `
    <div class="stat-grid" aria-label="Ticketkennzahlen">
      <article class="stat"><span class="stat-icon stat-icon--blue"><svg lucideInbox [size]="18"></svg></span><div><span>Offene Tickets</span><strong>{{ open() }}</strong></div></article>
      <article class="stat"><span class="stat-icon stat-icon--red"><svg lucideTriangleAlert [size]="18"></svg></span><div><span>Kritische Incidents</span><strong>{{ critical() }}</strong></div></article>
      <article class="stat"><span class="stat-icon stat-icon--green"><svg lucideCircleCheck [size]="18"></svg></span><div><span>Heute gelöst</span><strong>{{ resolved() }}</strong></div></article>
      <article class="stat"><span class="stat-icon stat-icon--amber"><svg lucideClock3 [size]="18"></svg></span><div><span>In Bearbeitung</span><strong>{{ progress() }}</strong></div></article>
    </div>
  `,
  styleUrl: './ticket-statistics.scss',
})
export class TicketStatistics {
  readonly open = input.required<number>();
  readonly critical = input.required<number>();
  readonly resolved = input.required<number>();
  readonly progress = input.required<number>();
}
