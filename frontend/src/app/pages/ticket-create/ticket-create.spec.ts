import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { TicketCreate } from './ticket-create';
import { API_URL } from '../../core/api-url';

describe('TicketCreate', () => {
  let fixture: ComponentFixture<TicketCreate>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TicketCreate], providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
    fixture = TestBed.createComponent(TicketCreate);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });
  afterEach(() => http.verify());

  function fillTitle(value: string): void {
    const input = fixture.nativeElement.querySelector('input[name=title]') as HTMLInputElement;
    input.value = value;
    input.dispatchEvent(new Event('input'));
    fixture.detectChanges();
  }
  function submit(): void {
    fixture.nativeElement.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    fixture.detectChanges();
  }

  it('rejects whitespace titles and focuses the invalid field', () => {
    fillTitle('   ');
    submit();
    expect(fixture.nativeElement.querySelector('[role=alert]').textContent).toContain('Titel eingeben');
    expect(document.activeElement).toBe(fixture.nativeElement.querySelector('input[name=title]'));
    http.expectNone(`${API_URL}/tickets`);
  });

  it('prevents duplicate submissions and links the created ticket to its confirmation', () => {
    const navigate = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    fillTitle('  VPN-Ausfall  ');
    submit();
    submit();
    const request = http.expectOne(`${API_URL}/tickets`);
    expect(request.request.body.title).toBe('VPN-Ausfall');
    request.flush({ id: 42 });
    expect(navigate).toHaveBeenCalledWith(['/dashboard'], { queryParams: { created: 42 } });
  });

  it('keeps form input after a server error', () => {
    fillTitle('VPN-Ausfall');
    submit();
    http.expectOne(`${API_URL}/tickets`).flush({}, { status: 503, statusText: 'Unavailable' });
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('input[name=title]').value).toBe('VPN-Ausfall');
    expect(fixture.nativeElement.querySelector('button[type=submit]').disabled).toBe(false);
    expect(fixture.nativeElement.querySelector('[role=alert]').textContent).toContain('nicht erstellt');
  });
});
