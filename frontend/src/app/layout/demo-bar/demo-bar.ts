import { Component, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { Router } from '@angular/router';

import { Auth, CurrentUser } from '../../core/auth/auth';
import { errorMessageFor } from '../../core/http-error-message';

// Reihenfolge und Beschriftung der Rollen im Umschalter - dieselben Begriffe
// wie in der Kopfzeile (main-layout.ts).
const ROLE_OPTIONS: { role: CurrentUser['role']; label: string }[] = [
  { role: 'employee', label: 'Mitarbeitende' },
  { role: 'agent', label: 'Support' },
  { role: 'admin', label: 'Administration' },
];

/**
 * Hinweisleiste und Rollen-Umschalter der oeffentlichen Demo. Erscheint nur,
 * wenn das angemeldete Konto zu einem Demo-Arbeitsbereich gehoert
 * (demo_expires_at gesetzt) - bei normalen Konten rendert sie nichts.
 * Eigene Komponente statt Teil von MainLayout: dessen Stylesheet laege sonst
 * ueber dem Groessenbudget pro Komponente (angular.json), und der Rahmen
 * muss von der Demo nichts wissen.
 */
@Component({
  selector: 'app-demo-bar',
  imports: [DatePipe],
  template: `
    @if (expiresAt(); as expires) {
      <section class="demo-bar" aria-label="Demo-Arbeitsbereich">
        <p><strong>Demo-Arbeitsbereich</strong> – nur für dich sichtbar, wird am {{ expires | date: 'dd.MM.yyyy, HH:mm' }} Uhr gelöscht.</p>
        <!-- role="group" + aria-label fasst die drei Buttons fuer Screenreader
             als eine Auswahl zusammen; aria-pressed markiert die aktive Rolle. -->
        <div class="demo-roles" role="group" aria-label="Rolle wechseln">
          <span>Ansicht als</span>
          @for (option of roles; track option.role) {
            <button type="button" [attr.aria-pressed]="currentRole() === option.role" [disabled]="isSwitching()" (click)="switchTo(option.role)">{{ option.label }}</button>
          }
        </div>
        @if (error()) { <p class="demo-error" role="alert">{{ error() }}</p> }
      </section>
    }
  `,
  styles: `
    .demo-bar { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: .6rem 1.5rem; padding: .7rem 2.25rem; border-bottom: 1px solid #cce3d6; background: #f0f8f3; color: #21593e; font-size: 12px; }
    p { margin: 0; }
    .demo-roles { display: flex; flex-wrap: wrap; align-items: center; gap: .4rem; }
    button { min-height: 32px; padding: .35rem .7rem; border: 1px solid #b5d8cc; border-radius: 6px; background: white; color: #21593e; font-size: 12px; font-weight: 600; }
    button[aria-pressed='true'] { border-color: var(--accent); background: var(--accent); color: white; }
    button:disabled { opacity: .6; }
    .demo-error { flex-basis: 100%; color: #94303a; }
    @media (max-width: 70rem) { .demo-bar { padding-inline: 1.5rem; } }
    @media (max-width: 48rem) { .demo-bar { padding-inline: 1rem; } }
  `,
})
export class DemoBar {
  private readonly auth = inject(Auth);
  private readonly router = inject(Router);
  protected readonly roles = ROLE_OPTIONS;
  protected readonly currentRole = computed(() => this.auth.currentUser()?.role);
  // null bei normalen Konten - dann zeigt das Template gar nichts an.
  protected readonly expiresAt = computed(() => this.auth.currentUser()?.demo_expires_at ?? null);
  protected readonly isSwitching = signal(false);
  protected readonly error = signal<string | null>(null);

  protected switchTo(role: CurrentUser['role']): void {
    if (this.isSwitching() || role === this.currentRole()) return;
    this.isSwitching.set(true);
    this.error.set(null);
    this.auth.switchDemoRole(role).subscribe({
      next: () => {
        this.isSwitching.set(false);
        // Das Dashboard laedt seine Liste selbst neu, sobald sich das Konto
        // aendert (siehe params in dashboard.ts) - hier nur dorthin wechseln.
        void this.router.navigateByUrl('/dashboard');
      },
      error: (error: unknown) => {
        this.isSwitching.set(false);
        this.error.set(errorMessageFor(error, {}, 'Die Rolle konnte nicht gewechselt werden. Bitte erneut versuchen.'));
      },
    });
  }
}
