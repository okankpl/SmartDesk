import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { Auth, CurrentUser } from './auth';
import { API_URL } from '../api-url';

const FAKE_USER: CurrentUser = {
  id: 1,
  email: 'max@smartdesk.local',
  full_name: 'Max Muster',
  role: 'employee',
};

// HttpTestingController laesst uns HTTP-Anfragen, die der Service ausloest,
// ABFANGEN statt wirklich ans Netzwerk zu schicken - man ruft expectOne(url)
// auf, um zu pruefen "genau eine Anfrage an diese URL wurde gemacht", und
// .flush(daten) simuliert die Server-Antwort. So laesst sich Auth komplett
// isoliert testen, ganz ohne laufendes Backend.
describe('Auth', () => {
  let auth: Auth;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    auth = TestBed.inject(Auth);
    httpMock = TestBed.inject(HttpTestingController);
  });

  // afterEach mit verify(): stellt sicher, dass in jedem Test WIRKLICH nur
  // die erwarteten Anfragen passiert sind - eine vergessene/unerwartete
  // zusaetzliche Anfrage wuerde den Test sonst unbemerkt durchlaufen lassen.
  afterEach(() => {
    httpMock.verify();
  });

  it('startet mit isLoggedIn() === false, solange niemand eingeloggt ist', () => {
    expect(auth.isLoggedIn()).toBe(false);
    expect(auth.currentUser()).toBeNull();
  });

  it('login() ruft POST /auth/login und danach GET /auth/me auf und setzt currentUser', () => {
    let result: CurrentUser | null | undefined;
    auth.login('max@smartdesk.local', 'geheim123').subscribe((user) => (result = user));

    // Die erste erwartete Anfrage: der Login-POST. form_data statt JSON, siehe
    // Kommentar dazu in auth.ts/backend/routers/auth.py.
    const loginReq = httpMock.expectOne(`${API_URL}/auth/login`);
    expect(loginReq.request.method).toBe('POST');
    loginReq.flush({ access_token: 'irrelevant-fuer-den-test', token_type: 'bearer' });

    // login() verkettet danach automatisch refreshCurrentUser() (switchMap in
    // auth.ts) - deshalb erwarten wir HIER eine ZWEITE Anfrage.
    const meReq = httpMock.expectOne(`${API_URL}/auth/me`);
    expect(meReq.request.method).toBe('GET');
    meReq.flush(FAKE_USER);

    expect(result).toEqual(FAKE_USER);
    expect(auth.currentUser()).toEqual(FAKE_USER);
    expect(auth.isLoggedIn()).toBe(true);
  });

  it('refreshCurrentUser() faengt einen 401 ab, statt den Fehler durchzureichen', () => {
    let result: CurrentUser | null | undefined;
    auth.refreshCurrentUser().subscribe((user) => (result = user));

    const req = httpMock.expectOne(`${API_URL}/auth/me`);
    // flush mit einem Fehler-Status simuliert eine echte 401-Antwort, z.B.
    // weil kein gueltiger Cookie da ist (nicht eingeloggt) - das ist ein
    // normaler, erwarteter Fall, kein Programmfehler (siehe catchError in auth.ts).
    req.flush('Ungueltige oder abgelaufene Anmeldedaten', { status: 401, statusText: 'Unauthorized' });

    expect(result).toBeNull();
    expect(auth.currentUser()).toBeNull();
    expect(auth.isLoggedIn()).toBe(false);
  });

  it('logout() setzt currentUser zurueck auf null', () => {
    // currentUser() ist read-only von aussen (asReadonly(), siehe auth.ts) -
    // fuer den Test-Ausgangszustand "eingeloggt" nutzen wir stattdessen einen
    // echten login()-Durchlauf statt eines internen Zugriffs.
    auth.login('max@smartdesk.local', 'geheim123').subscribe();
    httpMock.expectOne(`${API_URL}/auth/login`).flush({ access_token: 'x', token_type: 'bearer' });
    httpMock.expectOne(`${API_URL}/auth/me`).flush(FAKE_USER);
    expect(auth.isLoggedIn()).toBe(true);

    auth.logout().subscribe();
    httpMock.expectOne(`${API_URL}/auth/logout`).flush(null);

    expect(auth.isLoggedIn()).toBe(false);
    expect(auth.currentUser()).toBeNull();
  });
});
