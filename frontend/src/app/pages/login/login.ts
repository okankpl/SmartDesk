// @Component ist der Decorator, der eine Klasse zu einer Angular-Komponente
// macht (siehe Lernnotizen "Decorator") - die Metadaten im Objekt darunter
// (selector/imports/templateUrl/styleUrl) sagen Angular, wie/wo diese
// Komponente benutzt werden kann. inject() holt einen per Dependency
// Injection registrierten Service (hier: Auth, Router). signal() erzeugt
// einen reaktiven Wert-Container (siehe Lernnotizen "Signal/Computed").
import { Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Auth } from '../../core/auth/auth';

@Component({
  selector: 'app-login',
  // "imports" listet andere Standalone-Komponenten/Direktiven/Pipes auf, die
  // im Template (login.html) verwendet werden duerfen - hier leer, weil das
  // Formular ganz ohne Angulars FormsModule auskommt (siehe Kommentare unten).
  imports: [],
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

  // Eigener, lokaler Formular-Zustand als Signals statt Angulars
  // FormsModule/ReactiveFormsModule - bei nur zwei simplen Textfeldern
  // reicht das, ohne eine zusaetzliche Abhaengigkeit einzubinden (siehe YAGNI
  // in der Architektur-Doku). email()/password() lesen den aktuellen Wert,
  // .set(...) aendert ihn.
  protected readonly email = signal('');
  protected readonly password = signal('');
  protected readonly errorMessage = signal<string | null>(null);
  protected readonly isSubmitting = signal(false);

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

    this.errorMessage.set(null);
    this.isSubmitting.set(true);

    // .subscribe(...) "startet" ein Observable erst wirklich (siehe Lernnotizen
    // "RxJS") - vorher (in Auth.login) ist es nur eine Beschreibung, WAS
    // passieren soll, noch keine laufende Anfrage. next/error sind die zwei
    // moeglichen Ausgaenge: next bei Erfolg (mit dem Ergebnis als Parameter,
    // hier ungenutzt), error bei einer fehlgeschlagenen HTTP-Anfrage.
    this.auth.login(this.email(), this.password()).subscribe({
      next: () => {
        this.isSubmitting.set(false);
        this.router.navigateByUrl('/dashboard');
      },
      error: () => {
        // Bewusst dieselbe generische Meldung, egal ob Email unbekannt oder
        // Passwort falsch war - das Backend liefert absichtlich keinen
        // Unterschied (Anti-User-Enumeration, siehe Architektur-Doku Abschnitt 6).
        this.isSubmitting.set(false);
        this.errorMessage.set('E-Mail oder Passwort ist falsch.');
      },
    });
  }
}
