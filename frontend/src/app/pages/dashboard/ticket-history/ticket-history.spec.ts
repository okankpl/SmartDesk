import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TicketHistory } from './ticket-history';
import { API_URL } from '../../../core/api-url';

describe('TicketHistory', () => {
  beforeEach(() => TestBed.configureTestingModule({
    imports: [TicketHistory], providers: [provideHttpClient(), provideHttpClientTesting()],
  }));
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  it('shows actor, translated status and escaped content', async () => {
    const fixture = TestBed.createComponent(TicketHistory);
    fixture.componentRef.setInput('ticketId', 7);
    fixture.detectChanges();
    TestBed.inject(HttpTestingController).expectOne(`${API_URL}/tickets/7/history`).flush([{
      id: 1, kind: 'status_changed', actor_name: '<img src=x>', created_at: '2026-10-15T10:00:00Z',
      changes: { status: { old: 'open', new: 'in_progress' } },
    }]);
    await fixture.whenStable();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Offen → In Bearbeitung');
    expect(fixture.nativeElement.textContent).toContain('<img src=x>');
    expect(fixture.nativeElement.querySelector('img')).toBeNull();
  });

  it('shows assignee names instead of user ids and keeps free text untranslated', async () => {
    const fixture = TestBed.createComponent(TicketHistory);
    fixture.componentRef.setInput('ticketId', 7);
    fixture.detectChanges();
    TestBed.inject(HttpTestingController).expectOne(`${API_URL}/tickets/7/history`).flush([
      {
        id: 1, kind: 'status_changed', actor_name: 'Alex Weber', created_at: '2026-10-15T10:00:00Z',
        changes: { assignee_id: { old: null, new: 3, old_label: null, new_label: 'Alex Weber' } },
      },
      {
        // "critical" ist hier ein frei gewaehlter Titel, kein Prioritaetswert.
        id: 2, kind: 'updated', actor_name: 'Alex Weber', created_at: '2026-10-15T11:00:00Z',
        changes: { title: { old: 'Drucker', new: 'critical' } },
      },
    ]);
    await fixture.whenStable();
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Bearbeiter: — → Alex Weber');
    expect(text).not.toContain('Nutzer #3');
    expect(text).toContain('Titel: Drucker → critical');
    expect(text).not.toContain('Kritisch');
  });

  it('offers retry after a failed load', async () => {
    const fixture = TestBed.createComponent(TicketHistory);
    fixture.componentRef.setInput('ticketId', 7);
    fixture.detectChanges();
    const http = TestBed.inject(HttpTestingController);
    http.expectOne(`${API_URL}/tickets/7/history`).flush({}, { status: 500, statusText: 'Error' });
    await fixture.whenStable();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('nicht geladen');
    fixture.nativeElement.querySelector('button').click();
    fixture.detectChanges();
    http.expectOne(`${API_URL}/tickets/7/history`).flush([]);
    await fixture.whenStable();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('noch keine Änderungen');
  });
});
