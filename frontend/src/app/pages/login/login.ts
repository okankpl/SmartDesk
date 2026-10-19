// @Component ist der Decorator, der eine Klasse zu einer Angular-Komponente
// macht - die Metadaten im Objekt darunter
// (selector/imports/templateUrl/styleUrl) sagen Angular, wie/wo diese
// Komponente benutzt werden kann. inject() holt einen per Dependency
// Injection registrierten Service (hier: Auth, Router). signal() erzeugt
// einen reaktiven Wert-Container (siehe Kommentare in core/auth/auth.ts).
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
// ActivatedRoute beschreibt die gerade aktive Route samt URL-Parametern -
// hier gebraucht, um "?reason=session-expired" aus der URL zu lesen.
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Auth } from '../../core/auth/auth';
import { errorMessageFor } from '../../core/http-error-message';
import { LucideTicketCheck, LucideEye, LucideEyeOff, LucideArrowRight } from '@lucide/angular';

@Component({
  selector: 'app-login',
  // RouterLink verbindet die Anmeldung mit der Registrierung.
  imports: [RouterLink, LucideTicketCheck, LucideEye, LucideEyeOff, LucideArrowRight],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
  // "protected" statt "private": das Template (login.html) gehoert zur selben
  // Komponente und darf protected-Felder lesen/aufrufen, Code AUSSERHALB
  // dieser Klasse (z.B. eine andere Komponente) aber nicht - strenger als
  // "public", lockerer als "private".
  private readonly auth = inject(Auth);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  private cooldownTimer: ReturnType<typeof setInterval> | undefined;

  // true, wenn man wegen einer abgelaufenen Sitzung hierher umgeleitet wurde
  // (siehe session-expired-interceptor.ts). "snapshot" ist der Stand der URL
  // beim Erzeugen der Komponente - reicht hier, weil sich der Parameter
  // waehrend man auf der Login-Seite ist nicht mehr aendert. Deshalb auch
  // kein Signal: der Wert wird einmal gelesen und bleibt fest.
  protected readonly sessionExpired = this.route.snapshot.queryParamMap.get('reason') === 'session-expired';
  protected readonly accountCreated = this.route.snapshot.queryParamMap.get('registered') === '1';

  // Eigener, lokaler Formular-Zustand als Signals statt Angulars
  // FormsModule/ReactiveFormsModule - bei nur zwei simplen Textfeldern
  // reicht das (YAGNI). FormsModule kommt erst bei den groesseren Formularen
  // zum Einsatz (Ticket-Editor, Filter). email()/password() lesen den
  // aktuellen Wert, .set(...) aendert ihn.
  protected readonly email = signal('');
  protected readonly password = signal('');
  protected readonly errorMessage = signal<string | null>(null);
  protected readonly isSubmitting = signal(false);
  protected readonly passwordVisible = signal(false);
  protected readonly retryAfterSeconds = signal(0);

  constructor() {
    this.destroyRef.onDestroy(() => clearInterval(this.cooldownTimer));
  }

  private startCooldown(error: unknown): void {
    if (!(error instanceof HttpErrorResponse) || ![429, 503].includes(error.status)) return;
    const header = error.headers.get('Retry-After') ?? '';
    const parsed = Number(header);
    const seconds = /^\d+$/.test(header) && Number.isSafeInteger(parsed) && parsed > 0
      ? Math.min(parsed, 86400) : 30;
    const deadline = Date.now() + seconds * 1000;
    clearInterval(this.cooldownTimer);
    this.retryAfterSeconds.set(seconds);
    this.cooldownTimer = setInterval(() => {
      // Mit der tatsaechlich verstrichenen Zeit rechnen: Browser drosseln Timer
      // in Hintergrund-Tabs, das darf die angezeigte Wartezeit nicht verlaengern.
      const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      this.retryAfterSeconds.set(remaining);
      if (remaining === 0) clearInterval(this.cooldownTimer);
    }, 1000);
  }

  // Wird bei jedem Tastendruck im E-Mail-Feld aufgerufen (siehe (input)-Bindung
  // in login.html). event.target ist laut TypeScript nur ein generisches
  // "EventTarget" - "as HTMLInputElement" sagt dem Compiler "vertrau mir, das
  // ist wirklich ein <input>-Element", damit .value ueberhaupt erlaubt ist.
  protected onEmailInput(event: Event): void {
    this.email.set((event.target as HTMLInputElement).value);
  }

  protected onPasswordInput(event: Event): void {
    this.password.set((event.target as HTMLInputElement).value);
  }

  protected submit(event: Event): void {
    // Verhindert den nativen Formular-Submit (kompletter Seiten-Reload) -
    // stattdessen soll Angular die Anfrage per HttpClient im Hintergrund senden.
    event.preventDefault();
    if (this.isSubmitting() || this.retryAfterSeconds() > 0) return;

    this.errorMessage.set(null);
    this.isSubmitting.set(true);

    // .subscribe(...) "startet" ein Observable erst wirklich - vorher (in
    // Auth.login) ist es nur eine Beschreibung, WAS
    // passieren soll, noch keine laufende Anfrage. next/error sind die zwei
    // moeglichen Ausgaenge: next bei Erfolg (mit dem Ergebnis als Parameter,
    // hier ungenutzt), error bei einer fehlgeschlagenen HTTP-Anfrage.
    this.auth.login(this.email(), this.password()).subscribe({
      next: () => {
        this.isSubmitting.set(false);
        this.router.navigateByUrl('/dashboard');
      },
      error: (error: unknown) => {
        // 401: bewusst dieselbe Meldung, egal ob E-Mail unbekannt oder
        // Passwort falsch war - das Backend liefert absichtlich keinen
        // Unterschied (Anti-User-Enumeration, siehe Architektur-Doku Abschnitt 6).
        // Alles andere (Server aus, interner Fehler) ist KEIN falsches
        // Passwort und bekommt deshalb eine eigene Meldung.
        this.isSubmitting.set(false);
        this.startCooldown(error);
        this.errorMessage.set(
          errorMessageFor(
            error,
            {
              401: 'E-Mail oder Passwort ist falsch.',
              429: 'Zu viele Anmeldeversuche. Bitte warte und versuche es danach erneut.',
              503: 'Anmeldung vorübergehend nicht verfügbar. Bitte versuche es später erneut.',
            },
            'Anmeldung gerade nicht möglich. Bitte später erneut versuchen.',
          ),
        );
      },
    });
  }
}
