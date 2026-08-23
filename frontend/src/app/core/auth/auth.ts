import { Injectable, computed, signal } from '@angular/core';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Observable, catchError, of, switchMap, tap } from 'rxjs';

import { API_URL } from '../api-url';

// Feldnamen bewusst 1:1 wie im JSON vom Backend (snake_case, siehe UserRead in
// schemas/user.py) statt in TS-uebliches camelCase uebersetzt - es gibt aktuell
// keine Mapping-Schicht dazwischen, ein Alias hier waere nur eine weitere
// Fehlerquelle wie die, die genau das gerade verursacht hat.
export interface CurrentUser {
  id: number;
  email: string;
  full_name: string;
  role: 'employee' | 'agent' | 'admin';
}

@Injectable({ providedIn: 'root' })
export class Auth {
  // Der eingeloggte Nutzer. Kommt NIE aus dem JWT selbst (das Frontend sieht den
  // Token gar nicht, er steckt im HttpOnly-Cookie) - sondern immer aus einer
  // Antwort von /auth/me, das den Cookie serverseitig auswertet.
  private readonly _currentUser = signal<CurrentUser | null>(null);
  readonly currentUser = this._currentUser.asReadonly();
  readonly isLoggedIn = computed(() => this._currentUser() !== null);

  constructor(private readonly http: HttpClient) {}

  /**
   * Loggt ein und laedt danach den aktuellen Nutzer nach. Das Backend gibt im
   * JSON-Body zwar zusaetzlich einen access_token zurueck (fuer Swagger UI/curl),
   * der wird hier bewusst NIE gelesen oder gespeichert - der Browser haelt den
   * eigentlich gueltigen Token stattdessen unsichtbar im HttpOnly-Cookie.
   */
  login(email: string, password: string): Observable<CurrentUser | null> {
    // /auth/login erwartet Formular-Daten (OAuth2PasswordRequestForm), kein JSON -
    // siehe Kommentar dazu in backend/app/routers/auth.py.
    const body = new HttpParams().set('username', email).set('password', password);
    const headers = new HttpHeaders({ 'Content-Type': 'application/x-www-form-urlencoded' });

    return this.http
      .post(`${API_URL}/auth/login`, body.toString(), { headers })
      .pipe(switchMap(() => this.refreshCurrentUser()));
  }

  logout(): Observable<void> {
    return this.http.post<void>(`${API_URL}/auth/logout`, {}).pipe(tap(() => this._currentUser.set(null)));
  }

  /**
   * Fragt /auth/me ab und aktualisiert das currentUser-Signal entsprechend.
   * Wird zweimal gebraucht: nach einem erfolgreichen Login (s.o.) UND beim
   * Start der App (siehe app.config.ts), um nach einem Seiten-Reload zu pruefen,
   * ob der Cookie noch gueltig ist. catchError statt den Fehler durchzureichen,
   * weil "nicht eingeloggt" hier ein normaler, erwarteter Zustand ist - kein
   * Programmfehler.
   */
  refreshCurrentUser(): Observable<CurrentUser | null> {
    return this.http.get<CurrentUser>(`${API_URL}/auth/me`).pipe(
      tap((user) => this._currentUser.set(user)),
      catchError(() => {
        this._currentUser.set(null);
        return of(null);
      }),
    );
  }
}
