import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';

import { Login } from './login';
import { API_URL } from '../../core/api-url';

// Baut die Login-Seite mit einer vorgegebenen URL-Abfrage (z.B.
// "?reason=session-expired"). Statt echter Navigation wird ActivatedRoute
// durch ein kleines Ersatz-Objekt mit genau dem Teil ersetzt, den Login
// liest (snapshot.queryParamMap). convertToParamMap macht aus einem
// einfachen Objekt dieselbe ParamMap, die der Router selbst liefern wuerde.
function createLogin(queryParams: Record<string, string> = {}): ComponentFixture<Login> {
  TestBed.configureTestingModule({
    imports: [Login],
    providers: [
      provideHttpClient(),
      provideHttpClientTesting(),
      provideRouter([]),
      { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(queryParams) } } },
    ],
  });
  const fixture = TestBed.createComponent(Login);
  fixture.detectChanges();
  return fixture;
}

// Fuellt beide Felder so aus, wie es ein Mensch tun wuerde (Wert setzen +
// "input"-Ereignis, auf das (input)="..." im Template hoert) und schickt
// das Formular ab.
function submitCredentials(root: HTMLElement): void {
  for (const [selector, value] of [
    ['input[type=email]', 'max@example.com'],
    ['input[type=password]', 'geheim123'],
  ]) {
    const input = root.querySelector<HTMLInputElement>(selector)!;
    input.value = value;
    input.dispatchEvent(new Event('input'));
  }
  root.querySelector('form')!.dispatchEvent(new Event('submit'));
}

describe('Login', () => {
  afterEach(() => {
    TestBed.inject(HttpTestingController).verify();
    vi.useRealTimers();
  });

  it('zeigt einen Hinweis, wenn man wegen abgelaufener Sitzung umgeleitet wurde', () => {
    const root = createLogin({ reason: 'session-expired' }).nativeElement as HTMLElement;

    expect(root.querySelector('[role=status]')?.textContent).toContain('Sitzung ist abgelaufen');
  });

  it('zeigt keinen Hinweis bei einem normalen Aufruf der Login-Seite', () => {
    const root = createLogin().nativeElement as HTMLElement;

    expect(root.querySelector('[role=status]')).toBeNull();
  });

  it('meldet "E-Mail oder Passwort ist falsch" nur bei einem echten 401', () => {
    const fixture = createLogin();
    const root = fixture.nativeElement as HTMLElement;

    submitCredentials(root);
    TestBed.inject(HttpTestingController)
      .expectOne(`${API_URL}/auth/login`)
      .flush('Ungültige Anmeldedaten', { status: 401, statusText: 'Unauthorized' });
    fixture.detectChanges();

    expect(root.querySelector('[role=alert]')?.textContent).toContain('E-Mail oder Passwort ist falsch');
  });

  it('meldet "Server nicht erreichbar", wenn das Backend gar nicht antwortet', () => {
    const fixture = createLogin();
    const root = fixture.nativeElement as HTMLElement;

    submitCredentials(root);
    // .error(...) statt .flush(...): simuliert, dass GAR KEINE HTTP-Antwort
    // ankam (Backend aus) - HttpClient meldet das als status 0.
    TestBed.inject(HttpTestingController).expectOne(`${API_URL}/auth/login`).error(new ProgressEvent('error'));
    fixture.detectChanges();

    const message = root.querySelector('[role=alert]')?.textContent ?? '';
    expect(message).toContain('Server nicht erreichbar');
    expect(message).not.toContain('Passwort');
  });

  it('beachtet Retry-After, erhält Eingaben und verhindert Anfragen während der Wartezeit', () => {
    vi.useFakeTimers();
    const fixture = createLogin();
    const root = fixture.nativeElement as HTMLElement;
    const http = TestBed.inject(HttpTestingController);
    submitCredentials(root);
    http.expectOne(`${API_URL}/auth/login`).flush({}, {
      status: 429, statusText: 'Too Many Requests', headers: { 'Retry-After': '2' },
    });
    fixture.detectChanges();
    const button = root.querySelector<HTMLButtonElement>('button[type=submit]')!;
    expect(root.querySelector('[role=alert]')?.textContent).toContain('Zu viele Anmeldeversuche');
    expect(button.disabled).toBe(true);
    expect(button.textContent).toContain('Erneut in 2 s');
    expect(root.querySelector<HTMLInputElement>('input[type=email]')!.value).toBe('max@example.com');
    expect(root.querySelector<HTMLInputElement>('input[type=password]')!.value).toBe('geheim123');
    root.querySelector('form')!.dispatchEvent(new Event('submit'));
    http.expectNone(`${API_URL}/auth/login`);
    vi.advanceTimersByTime(1000);
    fixture.detectChanges();
    expect(button.textContent).toContain('Erneut in 1 s');
    vi.advanceTimersByTime(1000);
    fixture.detectChanges();
    expect(button.disabled).toBe(false);
    expect(button.textContent).toContain('Anmelden');
  });

  it.each([undefined, '-1', 'invalid', 'Infinity', '0'])('nutzt eine begrenzte Ersatzwartezeit bei ungültigem Retry-After %s', header => {
    vi.useFakeTimers();
    const fixture = createLogin();
    const root = fixture.nativeElement as HTMLElement;
    submitCredentials(root);
    TestBed.inject(HttpTestingController).expectOne(`${API_URL}/auth/login`).flush({}, {
      status: 429, statusText: 'Too Many Requests', headers: header ? { 'Retry-After': header } : {},
    });
    fixture.detectChanges();
    expect(root.querySelector('button[type=submit]')?.textContent).toContain('Erneut in 30 s');
    fixture.destroy();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('unterscheidet einen Ausfall des Login-Schutzes von falschen Zugangsdaten', () => {
    vi.useFakeTimers();
    const fixture = createLogin();
    const root = fixture.nativeElement as HTMLElement;
    submitCredentials(root);
    TestBed.inject(HttpTestingController).expectOne(`${API_URL}/auth/login`).flush({}, {
      status: 503, statusText: 'Service Unavailable', headers: { 'Retry-After': '30' },
    });
    fixture.detectChanges();
    expect(root.querySelector('[role=alert]')?.textContent).toContain('vorübergehend nicht verfügbar');
    expect(root.querySelector('[role=alert]')?.textContent).not.toContain('Passwort');
    expect(root.querySelector<HTMLButtonElement>('button[type=submit]')?.disabled).toBe(true);
  });
});
