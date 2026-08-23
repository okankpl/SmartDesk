import { inject } from '@angular/core';
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
    return true;
  }

  return router.createUrlTree(['/login']);
};
