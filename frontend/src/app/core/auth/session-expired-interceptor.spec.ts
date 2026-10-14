import { TestBed } from '@angular/core/testing';
import { HttpClient, HttpErrorResponse, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router, provideRouter } from '@angular/router';

import { Auth, CurrentUser } from './auth';
import { sessionExpiredInterceptor } from './session-expired-interceptor';
import { API_URL } from '../api-url';

const FAKE_USER: CurrentUser = { id: 1, email: 'max@example.com', full_name: 'Max Muster', role: 'employee' };

describe('sessionExpiredInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let auth: Auth;
  let navigate: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        // Derselbe Interceptor wie in app.config.ts, gegen einen gemockten
        // HttpClient (siehe auth.spec.ts fuer HttpTestingController).
        provideHttpClient(withInterceptors([sessionExpiredInterceptor])),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
    });
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
    auth = TestBed.inject(Auth);
    // vi.spyOn ersetzt router.navigate durch eine Attrappe, die nur
    // mitschreibt, womit sie aufgerufen wurde - der Test soll pruefen, OB
    // umgeleitet wird, nicht wirklich navigieren.
    navigate = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
  });

  afterEach(() => httpMock.verify());

  // Ausgangszustand "eingeloggt" ueber den echten Weg (/auth/me), wie in auth.spec.ts.
  function logIn(): void {
    auth.refreshCurrentUser().subscribe();
    httpMock.expectOne(`${API_URL}/auth/me`).flush(FAKE_USER);
  }

  it('schickt bei 401 waehrend einer Sitzung zum Login und vergisst den Nutzer', () => {
    logIn();

    // error: () => {} - der Fehler wird absichtlich geschluckt, damit er im
    // Test nicht als "unbehandelt" gemeldet wird.
    http.get(`${API_URL}/tickets`).subscribe({ error: () => {} });
    httpMock.expectOne(`${API_URL}/tickets`).flush('abgelaufen', { status: 401, statusText: 'Unauthorized' });

    expect(auth.isLoggedIn()).toBe(false);
    expect(navigate).toHaveBeenCalledWith(['/login'], { queryParams: { reason: 'session-expired' } });
  });

  it('leitet NICHT um, wenn niemand eingeloggt war (z.B. falsches Passwort beim Login)', () => {
    http.post(`${API_URL}/auth/login`, '').subscribe({ error: () => {} });
    httpMock.expectOne(`${API_URL}/auth/login`).flush('falsch', { status: 401, statusText: 'Unauthorized' });

    expect(navigate).not.toHaveBeenCalled();
  });

  it('reicht andere Fehler unveraendert an den Aufrufer weiter, ohne umzuleiten', () => {
    logIn();
    let receivedStatus: number | undefined;

    http.get(`${API_URL}/tickets`).subscribe({ error: (error: HttpErrorResponse) => (receivedStatus = error.status) });
    httpMock.expectOne(`${API_URL}/tickets`).flush('kaputt', { status: 500, statusText: 'Server Error' });

    expect(receivedStatus).toBe(500);
    expect(auth.isLoggedIn()).toBe(true);
    expect(navigate).not.toHaveBeenCalled();
  });
});
