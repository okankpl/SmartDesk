import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TicketEditor } from './ticket-editor';
import { Ticket } from '../../../core/tickets/ticket';
import { API_URL } from '../../../core/api-url';

const ticket: Ticket = {
  id: 42, version: 3, title: 'VPN-Ausfall', description: 'Ursprüngliche Beschreibung', priority: 'high',
  status: 'open', requester_id: 1, assignee_id: null, created_at: '2026-10-15T10:00:00Z',
  updated_at: '2026-10-15T10:00:00Z', resolved_at: null, closed_at: null, allowed_transitions: ['in_progress'],
};
const url = `${API_URL}/tickets/42`;

describe('TicketEditor', () => {
  let fixture: ComponentFixture<TicketEditor>;
  let http: HttpTestingController;
  let root: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TicketEditor], providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    fixture = TestBed.createComponent(TicketEditor);
    fixture.componentRef.setInput('ticket', ticket);
    root = fixture.nativeElement;
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  });
  afterEach(() => http.verify());

  function fill(name: string, value: string): void {
    const field = root.querySelector<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>(`[name=${name}]`)!;
    field.value = value;
    field.dispatchEvent(new Event(name === 'priority' ? 'change' : 'input'));
    fixture.detectChanges();
  }
  function submit(): void {
    root.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    fixture.detectChanges();
  }

  it('prefills all fields and does not submit unchanged content', () => {
    expect(root.querySelector<HTMLInputElement>('[name=title]')!.value).toBe(ticket.title);
    expect(root.querySelector<HTMLTextAreaElement>('[name=description]')!.value).toBe(ticket.description);
    expect(root.querySelector<HTMLSelectElement>('[name=priority]')!.value).toBe('high');
    expect(fixture.componentInstance.dirty()).toBe(false);
    submit();
    http.expectNone(url);
  });

  it('sends only changed content with its base version and prevents duplicate requests', async () => {
    const saved = vi.fn();
    fixture.componentInstance.saved.subscribe(saved);
    fill('title', '  Neuer Titel  ');
    submit();
    submit();
    const request = http.expectOne(url);
    expect(request.request.method).toBe('PATCH');
    expect(request.request.body).toEqual({ title: 'Neuer Titel', expected_version: 3 });
    await fixture.whenStable();
    fixture.detectChanges();
    expect(root.querySelector<HTMLInputElement>('[name=title]')!.disabled).toBe(true);
    const updated = { ...ticket, title: 'Neuer Titel', version: 4 };
    request.flush(updated);
    expect(saved).toHaveBeenCalledExactlyOnceWith(updated);
  });

  it('allows clearing the optional description and updating priority', () => {
    fill('description', '   ');
    fill('priority', 'critical');
    submit();
    const request = http.expectOne(url);
    expect(request.request.body).toEqual({ description: null, priority: 'critical', expected_version: 3 });
    request.flush({ ...ticket, description: null, priority: 'critical', version: 4 });
  });

  it('rejects whitespace titles and focuses the invalid field', () => {
    fill('title', '   ');
    submit();
    expect(root.querySelector('[role=alert]')?.textContent).toContain('Titel eingeben');
    expect(document.activeElement).toBe(root.querySelector('[name=title]'));
    http.expectNone(url);
  });

  it('retains the draft and enables retry after a server error', () => {
    fill('title', 'Mein Entwurf');
    submit();
    http.expectOne(url).flush({}, { status: 503, statusText: 'Unavailable' });
    fixture.detectChanges();
    expect(root.querySelector<HTMLInputElement>('[name=title]')!.value).toBe('Mein Entwurf');
    expect(root.querySelector('[role=alert]')?.textContent).toContain('nicht gespeichert');
    expect(fixture.componentInstance.busy()).toBe(false);
    expect(fixture.componentInstance.conflict()).toBe(false);
    submit();
    http.expectOne(url).flush({ ...ticket, title: 'Mein Entwurf', version: 4 });
  });

  it('keeps conflicting drafts until the current version is explicitly reloaded', async () => {
    fill('title', 'Veralteter Entwurf');
    submit();
    http.expectOne(url).flush({}, { status: 409, statusText: 'Conflict' });
    fixture.detectChanges();
    expect(root.querySelector<HTMLInputElement>('[name=title]')!.value).toBe('Veralteter Entwurf');
    expect(fixture.componentInstance.conflict()).toBe(true);
    submit();
    http.expectNone(url);
    fixture.componentInstance.reloaded.subscribe(value => fixture.componentRef.setInput('ticket', value));
    root.querySelector<HTMLButtonElement>('.reload-button')!.click();
    const request = http.expectOne(url);
    expect(request.request.method).toBe('GET');
    request.flush({ ...ticket, title: 'Neuer Serverstand', version: 5 });
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(root.querySelector<HTMLInputElement>('[name=title]')!.value).toBe('Neuer Serverstand');
    expect(fixture.componentInstance.dirty()).toBe(false);
    expect(fixture.componentInstance.conflict()).toBe(false);
    fill('title', 'Überarbeiteter Entwurf');
    submit();
    const retry = http.expectOne(url);
    expect(retry.request.body.expected_version).toBe(5);
    retry.flush({ ...ticket, title: 'Überarbeiteter Entwurf', version: 6 });
  });

  it('preserves the conflicting draft when reloading fails', () => {
    fill('title', 'Mein Entwurf');
    submit();
    http.expectOne(url).flush({}, { status: 409, statusText: 'Conflict' });
    fixture.detectChanges();
    root.querySelector<HTMLButtonElement>('.reload-button')!.click();
    http.expectOne(url).flush({}, { status: 503, statusText: 'Unavailable' });
    fixture.detectChanges();
    expect(root.querySelector<HTMLInputElement>('[name=title]')!.value).toBe('Mein Entwurf');
    expect(fixture.componentInstance.busy()).toBe(false);
    expect(fixture.componentInstance.conflict()).toBe(true);
    expect(root.querySelector('[role=alert]')?.textContent).toContain('Entwurf bleibt erhalten');
  });
});
