import { Component, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { Auth } from '../../core/auth/auth';
import { errorMessageFor } from '../../core/http-error-message';
import { LucideTicketCheck, LucideArrowRight } from '@lucide/angular';

@Component({
  selector: 'app-register',
  imports: [RouterLink, LucideTicketCheck, LucideArrowRight],
  templateUrl: './register.html',
  styleUrl: '../login/login.scss',
})
export class Register {
  private readonly auth = inject(Auth);
  private readonly router = inject(Router);
  protected readonly isSubmitting = signal(false);
  protected readonly errorMessage = signal<string | null>(null);
  protected readonly passwordVisible = signal(false);

  protected submit(event: Event): void {
    event.preventDefault();
    if (this.isSubmitting()) return;
    const form = event.target as HTMLFormElement;
    if (!form.reportValidity()) return;
    const fields = new FormData(form);
    const password = String(fields.get('password') ?? '');
    if (password !== fields.get('confirmation')) {
      this.errorMessage.set('Die Passwörter stimmen nicht überein.');
      return;
    }
    if (new TextEncoder().encode(password).length > 72) {
      this.errorMessage.set('Das Passwort darf höchstens 72 Bytes lang sein.');
      return;
    }
    this.isSubmitting.set(true);
    this.errorMessage.set(null);
    this.auth.register({
      full_name: String(fields.get('full_name') ?? '').trim(),
      email: String(fields.get('email') ?? '').trim(),
      password,
    }).subscribe({
      next: () => { void this.router.navigate(['/login'], { queryParams: { registered: '1' } }); },
      error: (error: unknown) => {
        this.isSubmitting.set(false);
        this.errorMessage.set(errorMessageFor(error, {
          // 403: auf dem oeffentlichen Demo-Server ist die Registrierung aus.
          403: 'Die Registrierung ist hier deaktiviert. Starte stattdessen die Demo auf der Anmeldeseite.',
          409: 'Diese E-Mail ist bereits registriert. Bitte melde dich an.',
          422: 'Bitte prüfe Name, E-Mail und Passwort.',
        }, 'Registrierung gerade nicht möglich. Bitte erneut versuchen.'));
      },
    });
  }
}
