import { ApplicationConfig, inject, provideAppInitializer, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { routes } from './app.routes';
import { Auth } from './core/auth/auth';
import { credentialsInterceptor } from './core/credentials-interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(withInterceptors([credentialsInterceptor])),
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
