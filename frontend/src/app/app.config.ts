import { ApplicationConfig, LOCALE_ID, inject, provideAppInitializer, provideBrowserGlobalErrorListeners } from '@angular/core';
import { registerLocaleData } from '@angular/common';
import localeDe from '@angular/common/locales/de';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { routes } from './app.routes';
import { Auth } from './core/auth/auth';
import { credentialsInterceptor } from './core/credentials-interceptor';

// Registriert die de-Locale-Daten (Monatsnamen, Datumsformate, ...) - ohne das
// wuerde z.B. der date-Pipe (siehe ticket-card.html) auf Englisch formatieren,
// obwohl der Rest der App durchgaengig deutsch ist.
registerLocaleData(localeDe);

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(withInterceptors([credentialsInterceptor])),
    { provide: LOCALE_ID, useValue: 'de-DE' },
    // Fragt einmalig /auth/me ab, BEVOR die App fertig startet (der Router also
    // Guards auswertet oder irgendeine Komponente rendert) - so weiss authGuard
    // beim allerersten Seitenaufruf/Reload sofort, ob der HttpOnly-Cookie noch
    // gueltig ist, statt kurz faelschlich "nicht eingeloggt" anzunehmen.
    provideAppInitializer(() => {
      const auth = inject(Auth);
      return firstValueFrom(auth.refreshCurrentUser());
    })
  ]
};
