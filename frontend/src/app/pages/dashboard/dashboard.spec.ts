import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { Dashboard } from './dashboard';
import { Ticket } from '../../core/tickets/ticket';
import { API_URL } from '../../core/api-url';

function makeTicket(overrides: Partial<Ticket>): Ticket {
  return {
    id: 1,
    title: 'Testticket',
    description: null,
    status: 'open',
    priority: 'medium',
    requester_id: 1,
    assignee_id: null,
    created_at: '2026-09-01T10:00:00',
    updated_at: '2026-09-01T10:00:00',
    resolved_at: null,
    closed_at: null,
    allowed_transitions: [],
    ...overrides,
  };
}

// Zwei Tickets, "heute" wirklich zum Testzeitpunkt geloest (new Date() statt
// eines festen Datums) - sonst wuerde dieser Test irgendwann in der Zukunft
// falsch werden, weil "heute" nicht mehr auf das feste Testdatum passt.
const TODAY_ISO = new Date().toISOString();

describe('Dashboard', () => {
  let fixture: ComponentFixture<Dashboard>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Dashboard],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(Dashboard);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  // Kleiner Helfer: startet das Laden (detectChanges), beantwortet die
  // GET-/tickets-Anfrage mit den uebergebenen Test-Tickets, und wartet, bis
  // resource() die Antwort verarbeitet und die Signals aktualisiert hat.
  async function loadWith(tickets: Ticket[]): Promise<void> {
    fixture.detectChanges();
    httpMock.expectOne(`${API_URL}/tickets`).flush(tickets);
    await fixture.whenStable();
    fixture.detectChanges();
  }

  it('zeigt waehrend des Ladens den Lade-Zustand, keine Kennzahlen', () => {
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Tickets werden geladen');

    // Offene Anfrage sauber beantworten, damit httpMock.verify() im
    // afterEach nicht faelschlich eine "haengende" Anfrage meldet.
    httpMock.expectOne(`${API_URL}/tickets`).flush([]);
  });

  it('berechnet die Kennzahlen korrekt aus den geladenen Tickets', async () => {
    await loadWith([
      makeTicket({ id: 1, status: 'open', priority: 'critical' }),
      makeTicket({ id: 2, status: 'open', priority: 'low' }),
      makeTicket({ id: 3, status: 'in_progress', priority: 'medium' }),
      // Bereits GESCHLOSSEN, obwohl kritisch - zaehlt bewusst NICHT als
      // aktiver Incident mehr (siehe criticalIncidentCount in dashboard.ts).
      makeTicket({ id: 4, status: 'closed', priority: 'critical' }),
      makeTicket({ id: 5, status: 'resolved', priority: 'high', resolved_at: TODAY_ISO }),
    ]);

    const component = fixture.componentInstance;
    expect(component['openTicketCount']()).toBe(2);
    expect(component['inProgressTicketCount']()).toBe(1);
    expect(component['criticalIncidentCount']()).toBe(1);
    expect(component['resolvedTodayCount']()).toBe(1);
  });

  it('wechselt die sichtbare Ticketliste beim Tab-Wechsel', async () => {
    await loadWith([
      makeTicket({ id: 1, status: 'open' }),
      makeTicket({ id: 2, status: 'in_progress' }),
    ]);

    const component = fixture.componentInstance;
    expect(component['visibleTickets']().map((t) => t.id)).toEqual([1]);

    component['setActiveView']('in_progress');
    expect(component['visibleTickets']().map((t) => t.id)).toEqual([2]);
  });

  it('zeigt eine Fehlermeldung, wenn das Laden fehlschlaegt', async () => {
    fixture.detectChanges();
    httpMock.expectOne(`${API_URL}/tickets`).flush('Serverfehler', { status: 500, statusText: 'Server Error' });
    await fixture.whenStable();
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('konnten nicht geladen werden');
  });
});
