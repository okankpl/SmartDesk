// ApplicationConfig ist der Typ fuer das Objekt, das beim Start der App an
// bootstrapApplication() (siehe main.ts) uebergeben wird - es sagt Angular,
// welche globalen Dienste ("Provider") der ganzen App zur Verfuegung stehen
// sollen. LOCALE_ID ist ein sogenanntes "Injection Token": ein Platzhalter-Wert,
// fuer den man per Dependency Injection (siehe Lernnotizen) etwas Konkretes
// hinterlegen kann - hier: welche Sprache/Region fuer Datums-/Zahlenformate
// gelten soll. inject() holt sich innerhalb einer Funktion (hier: dem
// App-Initializer weiter unten) einen per DI bereitgestellten Service, so wie
// es der Konstruktor einer Klasse sonst automatisch tut.
import { ApplicationConfig, LOCALE_ID, inject, provideAppInitializer, provideBrowserGlobalErrorListeners } from '@angular/core';

// registerLocaleData "installiert" die Formatierungsregeln fuer eine Sprache
// (Monatsnamen, Tausendertrennzeichen, Datumsreihenfolge, ...) im Speicher der
// App. localeDe ist ein von Angular mitgeliefertes Datenpaket genau dafuer -
// ohne den Import und die Registrierung unten wuerde Angular diese Daten gar
// nicht kennen, selbst wenn man LOCALE_ID auf 'de-DE' setzt.
import { registerLocaleData } from '@angular/common';
import localeDe from '@angular/common/locales/de';

// provideHttpClient aktiviert Angulars HttpClient-Service ueberhaupt erst fuer
// die App (ohne das wuerfe jeder inject(HttpClient) einen Fehler).
// withInterceptors(...) haengt eine Liste von Interceptor-Funktionen ein, die
// bei JEDER HTTP-Anfrage automatisch dazwischengeschaltet werden - siehe
// credentials-interceptor.ts fuer das, was unser einziger Interceptor tut.
import { provideHttpClient, withInterceptors } from '@angular/common/http';

// provideRouter aktiviert Angulars Router-Modul mit der Routenliste aus
// app.routes.ts (welche URL zeigt welche Komponente).
import { provideRouter } from '@angular/router';

// firstValueFrom wandelt ein RxJS-Observable (siehe Lernnotizen "RxJS") in ein
// natives JavaScript-Promise um - gebraucht, weil provideAppInitializer weiter
// unten ein Promise erwartet, unser Auth-Service aber (wie HttpClient ueblich)
// ein Observable zurueckgibt.
import { firstValueFrom } from 'rxjs';

import { routes } from './app.routes';
import { Auth } from './core/auth/auth';
import { credentialsInterceptor } from './core/credentials-interceptor';

// Registriert die de-Locale-Daten (Monatsnamen, Datumsformate, ...) - ohne das
// wuerde z.B. der date-Pipe (siehe ticket-card.html) auf Englisch formatieren,
// obwohl der Rest der App durchgaengig deutsch ist. Steht bewusst auf Modul-
// Ebene (kein "function"/"class" drumherum) - laeuft also einmal, sobald diese
// Datei beim App-Start importiert wird, genau wie das Modul-Ebene-Beispiel in
// backend/app/core/database.py.
registerLocaleData(localeDe);

export const appConfig: ApplicationConfig = {
  // "providers" ist eine Liste von Diensten/Konfigurationswerten, die per
  // Dependency Injection (DI) ueberall in der App per inject(...) oder per
  // Konstruktor-Parameter abgerufen werden koennen - das Angular-Gegenstueck
  // zu FastAPIs Depends(...)-System im Backend.
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(withInterceptors([credentialsInterceptor])),
    // Ein Objekt-Literal statt einer provideXyz()-Funktion: sagt DI direkt
    // "wenn irgendwo LOCALE_ID angefragt wird (z.B. intern vom date-Pipe),
    // liefere den festen Wert 'de-DE'".
    { provide: LOCALE_ID, useValue: 'de-DE' },
    // provideAppInitializer registriert eine Funktion, die Angular VOR dem
    // eigentlichen App-Start ausfuehrt und auf deren Ergebnis (falls ein
    // Promise/Observable zurueckkommt) es wartet, bevor irgendeine Route
    // aufgeloest oder Komponente gerendert wird.
    //
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
