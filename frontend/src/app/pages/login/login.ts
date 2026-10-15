// @Component ist der Decorator, der eine Klasse zu einer Angular-Komponente
// macht - die Metadaten im Objekt darunter
// (selector/imports/templateUrl/styleUrl) sagen Angular, wie/wo diese
// Komponente benutzt werden kann. inject() holt einen per Dependency
// Injection registrierten Service (hier: Auth, Router). signal() erzeugt
// einen reaktiven Wert-Container (siehe Kommentare in core/auth/auth.ts).
import { Component, inject, signal } from '@angular/core';
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

  // true, wenn man wegen einer abgelaufenen Sitzung hierher umgeleitet wurde
  // (siehe session-expired-interceptor.ts). "snapshot" ist der Stand der URL
  // beim Erzeugen der Komponente - reicht hier, weil sich der Parameter
  // waehrend man auf der Login-Seite ist nicht mehr aendert. Deshalb auch
  // kein Signal: der Wert wird einmal gelesen und bleibt fest.
  protected readonly sessionExpired = this.route.snapshot.queryParamMap.get('reason') === 'session-expired';
  protected readonly accountCreated = this.route.snapshot.queryParamMap.get('registered') === '1';

  // Eigener, lokaler Formular-Zustand als Signals statt Angulars
  // FormsModule/ReactiveFormsModule - bei nur zwei simplen Textfeldern
  // reicht das, ohne eine zusaetzliche Abhaengigkeit einzubinden (siehe YAGNI
  // in der Architektur-Doku). email()/password() lesen den aktuellen Wert,
  // .set(...) aendert ihn.
  protected readonly email = signal('');
  protected readonly password = signal('');
  protected readonly errorMessage = signal<string | null>(null);
  protected readonly isSubmitting = signal(false);
  protected readonly passwordVisible = signal(false);

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
    if (this.isSubmitting()) return;

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
        this.errorMessage.set(
          errorMessageFor(
            error,
            { 401: 'E-Mail oder Passwort ist falsch.' },
            'Anmeldung gerade nicht möglich. Bitte später erneut versuchen.',
          ),
        );
      },
    });
  }
}
