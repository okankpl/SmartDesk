// HttpErrorResponse ist die Klasse, in die HttpClient jede fehlgeschlagene
// Antwort verpackt - .status enthaelt den HTTP-Statuscode (z.B. 401).
import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
// catchError faengt einen Fehler im Datenstrom ab (siehe auth.ts).
// throwError(() => fehler) erzeugt ein Observable, das sofort mit genau
// diesem Fehler endet - so geht der Fehler nach unserer Reaktion trotzdem
// unveraendert an den eigentlichen Aufrufer (z.B. eine Komponente) weiter.
import { catchError, throwError } from 'rxjs';

import { Auth } from './auth';

/**
 * Reagiert an EINER Stelle auf eine abgelaufene Sitzung: antwortet das
 * Backend mit 401, obwohl das Frontend den Nutzer noch fuer eingeloggt
 * haelt, ist der JWT im Cookie abgelaufen (nach 60 Minuten, siehe
 * ACCESS_TOKEN_EXPIRE_MINUTES im Backend). Dann wird der Nutzer im Frontend
 * vergessen und zur Login-Seite geschickt, mit einem Hinweis, warum.
 *
 * Vorher blieb man in diesem Fall auf dem Dashboard, und jede Aktion
 * scheiterte nur mit einer allgemeinen Meldung (z.B. "Kommentar konnte nicht
 * gespeichert werden") - bis man von selbst auf die Idee kam, die Seite neu
 * zu laden. Als Interceptor statt in jeder Komponente einzeln, weil JEDE
 * Anfrage betroffen sein kann.
 */
export const sessionExpiredInterceptor: HttpInterceptorFn = (req, next) => {
  // inject() direkt im Interceptor: funktionale Interceptors laufen in einem
  // "Injection Context", inject() funktioniert hier also wie in einem
  // Konstruktor (siehe auth-guard.ts fuer dasselbe Prinzip bei Guards).
  const auth = inject(Auth);
  const router = inject(Router);

  return next(req).pipe(
    catchError((error: unknown) => {
      // Nur wenn der Nutzer bisher als eingeloggt galt: ein 401 beim Login
      // selbst (falsches Passwort) oder beim App-Start (/auth/me ohne
      // Cookie) ist ein normaler, erwarteter Fall und wird dort schon
      // behandelt - dort darf es keine Umleitung geben.
      if (error instanceof HttpErrorResponse && error.status === 401 && auth.isLoggedIn()) {
        auth.clearSession();
        // queryParams haengt "?reason=session-expired" an die URL an, die
        // Login-Seite zeigt daraufhin einen passenden Hinweis. "void" sagt
        // ausdruecklich: das Ergebnis von navigate() (ein Promise) wird hier
        // bewusst nicht abgewartet.
        void router.navigate(['/login'], { queryParams: { reason: 'session-expired' } });
      }
      return throwError(() => error);
    }),
  );
};
