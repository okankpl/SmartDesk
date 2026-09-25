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
// setzen/entfernen, beim Schliessen das "close"-Event feuern, auf das
// onDialogClosed() hoert), ohne den vollen Browser-Funktionsumfang
// (Fokus-Einfang, ::backdrop-Rendering) nachzubauen - der gehoert zum Browser
// selbst, hier geht es nur um UNSERE Komponentenlogik.
beforeAll(() => {
  if (!HTMLDialogElement.prototype.showModal) {
    HTMLDialogElement.prototype.showModal = function (this: HTMLDialogElement) {
      this.setAttribute('open', '');
    };
  }
  if (!HTMLDialogElement.prototype.close) {
    HTMLDialogElement.prototype.close = function (this: HTMLDialogElement) {
      this.removeAttribute('open');
      this.dispatchEvent(new Event('close'));
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

const COMMENTS_URL = `${API_URL}/tickets/1/comments`;

describe('TicketCard', () => {
  let fixture: ComponentFixture<TicketCard>;
  let httpMock: HttpTestingController;
  // Kurzform fuer das gerenderte DOM der Komponente, wird in fast jedem Test
  // gebraucht. "as HTMLElement" ist noetig, weil nativeElement als "any"
  // typisiert ist.
  let root: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TicketCard],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(TicketCard);
    httpMock = TestBed.inject(HttpTestingController);
    root = fixture.nativeElement as HTMLElement;
  });

  afterEach(() => httpMock.verify());

  // Klickt die Karte an (oeffnet das Popup). Dadurch entsteht der
  // Kommentarbereich und schickt seine GET-Anfrage ab - die wird hier mit
  // einer leeren Liste beantwortet, damit httpMock.verify() im afterEach
  // keine "haengende" Anfrage meldet. Was die Kommentar-Komponente mit der
  // Antwort macht, testet ticket-comments.spec.ts.
  async function openDetails(): Promise<void> {
    root.querySelector<HTMLButtonElement>('.ticket-card__trigger')!.click();
    fixture.detectChanges();
    httpMock.expectOne(COMMENTS_URL).flush([]);
    await fixture.whenStable();
    fixture.detectChanges();
  }

  it('zeigt die deutschen Status- und Prioritaets-Beschriftungen', () => {
    // setInput(...) ist der vorgesehene Weg, ein signal-basiertes input() in
    // einem Test zu setzen - ein direktes "component.ticket = ..." ginge
    // nicht, weil ticket() als Input schreibgeschuetzt ist.
    fixture.componentRef.setInput('ticket', makeTicket({ status: 'in_progress', priority: 'critical' }));
    fixture.detectChanges();

    const text = root.textContent ?? '';
    expect(text).toContain('In Bearbeitung');
    expect(text).toContain('Kritisch');
  });

  it('oeffnet und schliesst das Detail-Popup per Klick', async () => {
    fixture.componentRef.setInput('ticket', makeTicket());
    fixture.detectChanges();

    const dialog = root.querySelector('dialog') as HTMLDialogElement;
    expect(dialog.open).toBe(false);

    await openDetails();
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

    const buttonLabels = [...root.querySelectorAll('.ticket-detail__action')].map((el) => el.textContent?.trim());
    expect(buttonLabels).toEqual(['Schließen', 'Ablehnen']);
  });

  it('zeigt keine Aktions-Buttons, wenn allowed_transitions leer ist', () => {
    fixture.componentRef.setInput('ticket', makeTicket({ status: 'closed', allowed_transitions: [] }));
    fixture.detectChanges();

    expect(root.querySelectorAll('.ticket-detail__action').length).toBe(0);
  });

  it('ruft PATCH /tickets/{id}/status auf und feuert statusChanged bei Erfolg', () => {
    fixture.componentRef.setInput('ticket', makeTicket({ id: 42, status: 'open', allowed_transitions: ['in_progress'] }));
    fixture.detectChanges();

    let emitted = false;
    fixture.componentInstance.statusChanged.subscribe(() => (emitted = true));

    root.querySelector<HTMLButtonElement>('.ticket-detail__action')!.click();

    const req = httpMock.expectOne(`${API_URL}/tickets/42/status`);
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ status: 'in_progress' });
    req.flush(makeTicket({ id: 42, status: 'in_progress' }));

    expect(emitted).toBe(true);
  });

  describe('Kommentarbereich (Lazy Loading)', () => {
    beforeEach(() => {
      fixture.componentRef.setInput('ticket', makeTicket());
      fixture.detectChanges();
    });

    it('existiert nicht und laedt nichts, solange das Popup geschlossen ist', () => {
      // Der eigentliche Grund fuer das @if um <app-ticket-comments>: im
      // Dashboard existiert pro Ticket eine TicketCard - ohne diese Bedingung
      // gaebe es eine Anfrage pro Ticket, obwohl niemand ein Popup geoeffnet
      // hat. expectNone schlaegt fehl, falls doch eine passende Anfrage rausging.
      expect(root.querySelector('app-ticket-comments')).toBeNull();
      httpMock.expectNone(COMMENTS_URL);
    });

    it('entsteht beim Oeffnen und verschwindet beim Schliessen wieder', async () => {
      await openDetails();
      expect(root.querySelector('app-ticket-comments')).not.toBeNull();

      root.querySelector<HTMLButtonElement>('.ticket-detail__close')!.click();
      fixture.detectChanges();
      expect(root.querySelector('app-ticket-comments')).toBeNull();
    });

    it('laedt beim erneuten Oeffnen frisch vom Server', async () => {
      // Deckt onDialogClosed() ab: nach dem Schliessen wird die
      // Kommentar-Komponente zerstoert, beim naechsten Oeffnen neu erzeugt -
      // also muss eine ZWEITE Anfrage rausgehen (sonst saehe man Kommentare
      // anderer erst nach einem kompletten Seiten-Reload). openDetails()
      // enthaelt selbst schon expectOne(...), schlaegt also fehl, falls die
      // zweite Anfrage ausbleibt.
      await openDetails();
      root.querySelector<HTMLButtonElement>('.ticket-detail__close')!.click();
      fixture.detectChanges();

      await openDetails();
    });
  });
});
