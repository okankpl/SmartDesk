// @Injectable ist ein Decorator (siehe Lernnotizen "Decorator"), der eine
// Klasse als "Service" markiert, den Angular per Dependency Injection (DI) an
// andere Stellen der App verteilen kann. computed()/signal() sind Angulars
// Reaktivitaets-Bausteine (siehe Lernnotizen "Signal/Computed") - hier nutzen
// wir sie, um "wer ist eingeloggt" als reaktiven Zustand zu halten, den jede
// Komponente automatisch mitbekommt, sobald er sich aendert.
import { Injectable, computed, signal } from '@angular/core';
// HttpClient ist Angulars eingebauter Dienst fuer HTTP-Anfragen (das
// Frontend-Gegenstueck zu z.B. Pythons requests-Bibliothek). HttpHeaders/
// HttpParams sind Hilfsklassen, um Header bzw. Formular-/Query-Parameter
// unveraenderlich (immutable) und typsicher aufzubauen, statt rohe Strings
// zusammenzubauen.
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
// RxJS ist die Bibliothek hinter Angulars asynchronen Datenstroemen.
// Observable ist der Grundtyp dafuer (vergleichbar mit einem Promise, das aber
// mehrfach Werte liefern und man abbrechen kann). catchError/of/switchMap/tap
// sind "Operatoren" - kleine Funktionen, die man mit .pipe(...) aneinanderreiht,
// um einen Datenstrom zu transformieren, ohne ihn manuell "auszupacken".
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

// providedIn: 'root' heisst: Angular erzeugt GENAU EINE Instanz dieser Klasse
// fuer die ganze App (ein "Singleton") und reicht sie ueberall dorthin durch,
// wo sie per inject(Auth) oder Konstruktor-Parameter angefragt wird - deshalb
// funktioniert das currentUser-Signal unten als gemeinsamer, geteilter
// Zustand fuer die komplette Anwendung, nicht als Kopie pro Komponente.
@Injectable({ providedIn: 'root' })
export class Auth {
  // Der eingeloggte Nutzer. Kommt NIE aus dem JWT selbst (das Frontend sieht den
  // Token gar nicht, er steckt im HttpOnly-Cookie) - sondern immer aus einer
  // Antwort von /auth/me, das den Cookie serverseitig auswertet.
  //
  // Muster "privates beschreibbares Signal + oeffentliches Read-Only-Signal":
  // _currentUser darf nur INNERHALB dieser Klasse per .set(...) veraendert
  // werden, andere Komponenten duerfen currentUser() zwar LESEN, aber nicht
  // versehentlich von aussen ueberschreiben. asReadonly() gibt dafuer eine
  // abgespeckte Version des Signals zurueck, die kein .set()/.update() mehr hat.
  private readonly _currentUser = signal<CurrentUser | null>(null);
  readonly currentUser = this._currentUser.asReadonly();
  // computed() leitet einen Wert automatisch aus anderen Signals ab (hier: aus
  // currentUser) - jede Komponente, die isLoggedIn() im Template liest, wird
  // automatisch neu gerendert, sobald sich currentUser aendert, ganz ohne
  // manuelles "Bescheid geben".
  readonly isLoggedIn = computed(() => this._currentUser() !== null);

  // Angulars "Constructor Injection": schreibt man einen Parameter mit
  // private/readonly direkt in die Konstruktor-Klammer, erzeugt TypeScript
  // automatisch ein gleichnamiges Klassenfeld daraus UND Angular fuellt es per
  // DI mit der App-weiten HttpClient-Instanz - kuerzer als erst ein Feld zu
  // deklarieren und es dann im Konstruktor-Koerper zuzuweisen.
  constructor(private readonly http: HttpClient) {}

  /**
   * Loggt ein und laedt danach den aktuellen Nutzer nach. Das Backend gibt im
   * JSON-Body zwar zusaetzlich einen access_token zurueck (fuer Swagger UI/curl),
   * der wird hier bewusst NIE gelesen oder gespeichert - der Browser haelt den
   * eigentlich gueltigen Token stattdessen unsichtbar im HttpOnly-Cookie.
   */
  login(email: string, password: string): Observable<CurrentUser | null> {
    // /auth/login erwartet Formular-Daten (OAuth2PasswordRequestForm), kein JSON -
    // siehe Kommentar dazu in backend/app/routers/auth.py. HttpParams baut den
    // Body im Format "username=...&password=..." zusammen (inkl. URL-Escaping
    // von Sonderzeichen) - .toString() macht daraus den fertigen String, den
    // http.post() als Body verschickt.
    const body = new HttpParams().set('username', email).set('password', password);
    const headers = new HttpHeaders({ 'Content-Type': 'application/x-www-form-urlencoded' });

    return this.http
      .post(`${API_URL}/auth/login`, body.toString(), { headers })
      // .pipe(...) reiht Operatoren hintereinander, die auf das Ergebnis der
      // Anfrage angewendet werden, sobald es ankommt. switchMap "ersetzt" das
      // Login-Observable durch ein NEUES Observable (hier: refreshCurrentUser())
      // - das Ergebnis von login() ist also nicht die rohe Login-Antwort,
      // sondern direkt das Ergebnis von refreshCurrentUser().
      .pipe(switchMap(() => this.refreshCurrentUser()));
  }

  logout(): Observable<void> {
    // tap(...) fuehrt einen Seiteneffekt aus (hier: das Signal zuruecksetzen),
    // ohne den durchlaufenden Wert selbst zu veraendern - anders als switchMap
    // "ersetzt" tap das Observable NICHT, es beobachtet es nur.
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
      // catchError faengt einen Fehler im Datenstrom ab (hier: die 401-Antwort,
      // wenn kein gueltiger Cookie da ist) und ersetzt ihn durch ein neues,
      // FEHLERFREIES Observable - of(null) erzeugt ein Observable, das einfach
      // sofort den Wert null liefert. Ohne das wuerde jeder Aufrufer von
      // refreshCurrentUser() selbst einen try/catch-aehnlichen Fehlerpfad
      // brauchen, nur um "nicht eingeloggt" zu behandeln.
      catchError(() => {
        this._currentUser.set(null);
        return of(null);
      }),
    );
  }
}
