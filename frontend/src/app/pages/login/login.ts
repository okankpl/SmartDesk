import { Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Auth } from '../../core/auth/auth';

@Component({
  selector: 'app-login',
  imports: [],
  templateUrl: './login.html',
  styleUrl: './login.scss',
})
export class Login {
  private readonly auth = inject(Auth);
  private readonly router = inject(Router);

  protected readonly email = signal('');
  protected readonly password = signal('');
  protected readonly errorMessage = signal<string | null>(null);
  protected readonly isSubmitting = signal(false);

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
