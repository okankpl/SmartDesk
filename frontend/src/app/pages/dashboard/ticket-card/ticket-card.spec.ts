import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { TicketCard } from './ticket-card';
import { Ticket } from '../../../core/tickets/ticket';
import { API_URL } from '../../../core/api-url';

// jsdom (die DOM-Umgebung, in der diese Tests laufen - kein echter Browser)
// implementiert die IMPERATIVEN Methoden des <dialog>-Elements nicht
// (showModal()/close() fehlen, das reine "open"-Attribut wird aber normal
// unterstuetzt) - ein bekanntes, verbreitetes Test-Tooling-Problem, keine
// SmartDesk-Besonderheit. Minimaler Ersatz nur fuer die Testumgebung: bildet
// genau das nach, was ticket-card.ts tatsaechlich braucht (open-Attribut
// setzen/entfernen), ohne den vollen Browser-Funktionsumfang (Fokus-Einfang,
// ::backdrop-Rendering) nachzubauen - der ist im echten Browser laengst
// getestet (siehe die Browser-Automatisierungs-Checks aus dem Chat), hier
// geht es nur um UNSERE Komponentenlogik.
beforeAll(() => {
  if (!HTMLDialogElement.prototype.showModal) {
    HTMLDialogElement.prototype.showModal = function (this: HTMLDialogElement) {
      this.setAttribute('open', '');
    };
  }
  if (!HTMLDialogElement.prototype.close) {
    HTMLDialogElement.prototype.close = function (this: HTMLDialogElement) {
      this.removeAttribute('open');
    };
  }
});

// Baut ein vollstaendiges Test-Ticket, mit sinnvollen Defaults fuer alle
// Pflichtfelder und der Moeglichkeit, per Parameter genau die Felder zu
// ueberschreiben, die ein einzelner Test wirklich braucht - Partial<Ticket>
// heisst "irgendeine Teilmenge der Ticket-Felder", nicht alle.
function makeTicket(overrides: Partial<Ticket> = {}): Ticket {
  return {
    id: 1,
    title: 'Testticket',
    description: 'Eine Beschreibung',
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

describe('TicketCard', () => {
  let fixture: ComponentFixture<TicketCard>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TicketCard],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(TicketCard);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('zeigt die deutschen Status- und Prioritaets-Beschriftungen', () => {
    // setInput(...) ist der vorgesehene Weg, ein signal-basiertes input() in
    // einem Test zu setzen - ein direktes "component.ticket = ..." ginge
    // nicht, weil ticket() als Input schreibgeschuetzt ist.
    fixture.componentRef.setInput('ticket', makeTicket({ status: 'in_progress', priority: 'critical' }));
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('In Bearbeitung');
    expect(text).toContain('Kritisch');
  });

  it('oeffnet und schliesst das Detail-Popup per Klick', () => {
    fixture.componentRef.setInput('ticket', makeTicket());
    fixture.detectChanges();

    const root = fixture.nativeElement as HTMLElement;
    const dialog = root.querySelector('dialog') as HTMLDialogElement;
    expect(dialog.open).toBe(false);

    root.querySelector<HTMLButtonElement>('.ticket-card__trigger')!.click();
    expect(dialog.open).toBe(true);

    root.querySelector<HTMLButtonElement>('.ticket-detail__close')!.click();
    expect(dialog.open).toBe(false);
  });

  it('zeigt fuer jeden erlaubten Uebergang den passenden Aktions-Button', () => {
    // RESOLVED -> CLOSED und RESOLVED -> IN_PROGRESS haben unterschiedliche
    // Beschriftungen ("Schliessen" vs. "Ablehnen"), obwohl IN_PROGRESS an
    // anderer Stelle (von OPEN aus) "Uebernehmen" heisst - genau die
    // Fallunterscheidung aus TRANSITION_ACTION_LABELS in ticket-card.ts.
    fixture.componentRef.setInput(
      'ticket',
      makeTicket({ status: 'resolved', allowed_transitions: ['closed', 'in_progress'] }),
    );
    fixture.detectChanges();

    const buttonLabels = [...fixture.nativeElement.querySelectorAll('.ticket-detail__action')].map((el: HTMLElement) =>
      el.textContent?.trim(),
    );
    expect(buttonLabels).toEqual(['Schließen', 'Ablehnen']);
  });

  it('zeigt keine Aktions-Buttons, wenn allowed_transitions leer ist', () => {
    fixture.componentRef.setInput('ticket', makeTicket({ status: 'closed', allowed_transitions: [] }));
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelectorAll('.ticket-detail__action').length).toBe(0);
  });

  it('ruft PATCH /tickets/{id}/status auf und feuert statusChanged bei Erfolg', () => {
    fixture.componentRef.setInput('ticket', makeTicket({ id: 42, status: 'open', allowed_transitions: ['in_progress'] }));
    fixture.detectChanges();

    let emitted = false;
    fixture.componentInstance.statusChanged.subscribe(() => (emitted = true));

    (fixture.nativeElement as HTMLElement).querySelector<HTMLButtonElement>('.ticket-detail__action')!.click();

    const req = httpMock.expectOne(`${API_URL}/tickets/42/status`);
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ status: 'in_progress' });
    req.flush(makeTicket({ id: 42, status: 'in_progress' }));

    expect(emitted).toBe(true);
  });
});
