import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { TicketAssignment } from './ticket-assignment';
import { API_URL } from '../../../core/api-url';
import { Ticket } from '../../../core/tickets/ticket';

function makeTicket(overrides: Partial<Ticket>): Ticket {
  return {
    id: 7, version: 3, title: 'Drucker', description: null, status: 'in_progress', priority: 'medium',
    requester_id: 1, assignee_id: null, requester_name: 'Lena Fischer', assignee_name: null,
    created_at: '2026-10-15T10:00:00Z', updated_at: '2026-10-15T10:00:00Z',
    resolved_at: null, closed_at: null, allowed_transitions: [],
    ...overrides,
  };
}

const SUPPORT_STAFF = [
  { id: 3, email: 'agent@example.com', full_name: 'Alex Weber', role: 'agent' },
  { id: 4, email: 'admin@example.com', full_name: 'Samira Kaya', role: 'admin' },
  { id: 2, email: 'employee@example.com', full_name: 'Lena Fischer', role: 'employee' },
];

describe('TicketAssignment', () => {
  beforeEach(() => TestBed.configureTestingModule({
    imports: [TicketAssignment], providers: [provideHttpClient(), provideHttpClientTesting()],
  }));
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  async function renderWith(ticket: Ticket): Promise<HTMLSelectElement> {
    const fixture = TestBed.createComponent(TicketAssignment);
    fixture.componentRef.setInput('ticket', ticket);
    fixture.detectChanges();
    // Die Personen kommen erst nach dem ersten Rendern an - genau die
    // Reihenfolge, in der die Auswahl vorher die falsche Person zeigte.
    TestBed.inject(HttpTestingController).expectOne(`${API_URL}/users`).flush(SUPPORT_STAFF);
    await fixture.whenStable();
    fixture.detectChanges();
    return fixture.nativeElement.querySelector('select') as HTMLSelectElement;
  }

  it('preselects the current assignee even if it is not the first person in the list', async () => {
    const select = await renderWith(makeTicket({ assignee_id: 4, assignee_name: 'Samira Kaya' }));

    expect(select.value).toBe('4');
    expect(select.selectedOptions[0].textContent?.trim()).toBe('Samira Kaya');
  });

  it('preselects "Nicht zugewiesen" for an open ticket without assignee and lists only support staff', async () => {
    const select = await renderWith(makeTicket({ status: 'open', assignee_id: null }));

    expect(select.value).toBe('');
    expect([...select.options].map((option) => option.textContent?.trim())).toEqual([
      'Nicht zugewiesen', 'Alex Weber', 'Samira Kaya',
    ]);
  });
});
