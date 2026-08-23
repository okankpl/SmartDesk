// inject() holt sich innerhalb einer Funktion (statt ueber einen
// Konstruktor-Parameter) einen per Dependency Injection bereitgestellten
// Service - hier gebraucht, weil ein Route-Guard eine einfache Funktion ist,
// keine Klasse mit eigenem Konstruktor.
import { inject } from '@angular/core';
// CanActivateFn ist der Funktions-Typ, den Angular fuer einen Route-Guard
// erwartet: eine Funktion, die true (Zugriff erlaubt), false (Zugriff
// verweigert) oder - wie hier - eine Weiterleitung zurueckgeben kann.
import { CanActivateFn, Router } from '@angular/router';
import { Auth } from './auth';

// Laeuft vor dem Betreten einer geschuetzten Route. Zum Zeitpunkt, an dem der
// Router ueberhaupt Guards auswertet, ist der App-Initializer aus app.config.ts
// (der /auth/me beim Start abfragt) bereits abgeschlossen - isLoggedIn() ist
// hier also nie ein veralteter/unbestimmter Zwischenstand, sondern der
// tatsaechliche Session-Status.
export const authGuard: CanActivateFn = () => {
  const auth = inject(Auth);
  const router = inject(Router);

  if (auth.isLoggedIn()) {
    // true = "Navigation erlauben", die eigentlich angefragte Route wird geladen.
    return true;
  }

  // router.createUrlTree(...) baut eine interne Router-Repraesentation der
  // Ziel-URL, OHNE sofort dorthin zu navigieren. Ein Guard, der so ein
  // UrlTree-Objekt zurueckgibt (statt true/false), sagt dem Router damit
  // "leite stattdessen HIERHIN um" - der eleganteste Weg fuer eine
  // Guard-Umleitung, weil der Router die Navigation selbst uebernimmt.
  return router.createUrlTree(['/login']);
};
