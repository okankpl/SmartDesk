import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { TicketComments } from './ticket-comments';
import { TicketComment } from '../../../core/comments/comment';
import { Auth } from '../../../core/auth/auth';
import { API_URL } from '../../../core/api-url';

// Gleiches Muster wie makeTicket in ticket-card.spec.ts, nur fuer Kommentare.
function makeComment(overrides: Partial<TicketComment> = {}): TicketComment {
  return {
    id: 1,
    ticket_id: 1,
    author_id: 1,
    body: 'Testkommentar',
    created_at: '2026-09-01T11:00:00',
    ...overrides,
  };
}

const COMMENTS_URL = `${API_URL}/tickets/1/comments`;

describe('TicketComments', () => {
  let fixture: ComponentFixture<TicketComments>;
  let httpMock: HttpTestingController;
  let root: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TicketComments],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    fixture = TestBed.createComponent(TicketComments);
    httpMock = TestBed.inject(HttpTestingController);
    root = fixture.nativeElement as HTMLElement;
    fixture.componentRef.setInput('ticketId', 1);
  });

  afterEach(() => httpMock.verify());

  // Erstes detectChanges() startet resource() -> GET-Anfrage geht raus; die
  // wird mit den uebergebenen Kommentaren beantwortet, danach warten, bis
  // resource() die Antwort verarbeitet hat - wie loadWith() in dashboard.spec.ts.
  async function loadWith(comments: TicketComment[]): Promise<void> {
    fixture.detectChanges();
    httpMock.expectOne(COMMENTS_URL).flush(comments);
    await fixture.whenStable();
    fixture.detectChanges();
  }

  // Tippen simulieren: Wert setzen UND das "input"-Event feuern, auf das
  // (input)="onBodyInput($event)" im Template hoert - nur den Wert zu setzen,
  // wuerde Angular nicht mitbekommen.
  function typeComment(text: string): void {
    const textarea = root.querySelector('textarea')!;
    textarea.value = text;
    textarea.dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }

  function submitButton(): HTMLButtonElement {
    return root.querySelector<HTMLButtonElement>('.ticket-comments__submit')!;
  }

  it('zeigt waehrend des Ladens einen Lade-Hinweis', () => {
    fixture.detectChanges();

    expect(root.textContent).toContain('Kommentare werden geladen');

    httpMock.expectOne(COMMENTS_URL).flush([]);
  });

  it('zeigt die geladenen Kommentare an, eigene als "Du"', async () => {
    // Eingeloggten Nutzer (id 1) setzen: Auth kennt den aktuellen Nutzer
    // nur aus einer /auth/me-Antwort, also genau die simulieren.
    TestBed.inject(Auth).refreshCurrentUser().subscribe();
    httpMock
      .expectOne(`${API_URL}/auth/me`)
      .flush({ id: 1, email: 'max@test.local', full_name: 'Max Melder', role: 'employee' });

    await loadWith([
      makeComment({ id: 1, author_id: 1, body: 'Drucker zeigt Fehler E-04' }),
      makeComment({ id: 2, author_id: 3, body: 'Schaue ich mir an' }),
    ]);

    const items = root.querySelectorAll('.ticket-comments__item');
    expect(items.length).toBe(2);
    expect(items[0].textContent).toContain('Du');
    expect(items[0].textContent).toContain('Drucker zeigt Fehler E-04');
    expect(items[0].classList).toContain('ticket-comments__item--own');
    expect(items[1].textContent).toContain('Nutzer #3');
    expect(items[1].classList).not.toContain('ticket-comments__item--own');
  });

  it('zeigt einen Hinweis, wenn es noch keine Kommentare gibt', async () => {
    await loadWith([]);

    expect(root.textContent).toContain('Noch keine Kommentare.');
  });

  it('stellt Kommentartext als Text dar, nicht als HTML (XSS-Schutz)', async () => {
    await loadWith([makeComment({ body: '<img src=x onerror=alert(1)>' })]);

    const body = root.querySelector('.ticket-comments__body')!;
    // Der Text steht sichtbar da, es wurde aber KEIN <img>-Element erzeugt.
    expect(body.textContent).toBe('<img src=x onerror=alert(1)>');
    expect(body.querySelector('img')).toBeNull();
  });

  it('sendet einen neuen Kommentar per POST und haengt ihn an die Liste an', async () => {
    await loadWith([makeComment({ id: 1, body: 'Erster Kommentar' })]);

    typeComment('Danke, warte auf Rückmeldung');
    submitButton().click();

    const req = httpMock.expectOne(COMMENTS_URL);
    expect(req.request.method).toBe('POST');
    // Nur der Text - author_id/ticket_id schickt das Frontend bewusst nicht mit.
    expect(req.request.body).toEqual({ body: 'Danke, warte auf Rückmeldung' });
    req.flush(makeComment({ id: 2, body: 'Danke, warte auf Rückmeldung' }));
    fixture.detectChanges();

    const items = root.querySelectorAll('.ticket-comments__item');
    expect(items.length).toBe(2);
    // Neuer Kommentar landet UNTEN (chronologisch), ohne erneuten GET -
    // httpMock.verify() im afterEach wuerde eine zusaetzliche Anfrage melden.
    expect(items[1].textContent).toContain('Danke, warte auf Rückmeldung');
    expect(root.querySelector('textarea')!.value).toBe('');
  });

  it('deaktiviert den Senden-Button bei leerem oder nur-Leerzeichen-Text', async () => {
    await loadWith([]);
    expect(submitButton().disabled).toBe(true);

    typeComment('   ');
    expect(submitButton().disabled).toBe(true);

    typeComment('Jetzt mit Inhalt');
    expect(submitButton().disabled).toBe(false);
  });

  it('behaelt den Text und zeigt eine Meldung, wenn das Senden fehlschlaegt', async () => {
    await loadWith([]);

    typeComment('Wichtiger Hinweis');
    submitButton().click();
    httpMock.expectOne(COMMENTS_URL).flush('Serverfehler', { status: 500, statusText: 'Server Error' });
    fixture.detectChanges();

    expect(root.textContent).toContain('Kommentar konnte nicht gespeichert werden');
    expect(root.querySelector('textarea')!.value).toBe('Wichtiger Hinweis');
    expect(root.querySelectorAll('.ticket-comments__item').length).toBe(0);
  });

  it('zeigt eine Fehlermeldung und kein Formular, wenn das Laden fehlschlaegt', async () => {
    fixture.detectChanges();
    httpMock.expectOne(COMMENTS_URL).flush('Serverfehler', { status: 500, statusText: 'Server Error' });
    await fixture.whenStable();
    fixture.detectChanges();

    expect(root.textContent).toContain('Kommentare konnten nicht geladen werden');
    expect(root.querySelector('.ticket-comments__form')).toBeNull();
  });
});
