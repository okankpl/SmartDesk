// Grundfunktion zum Erstellen einer Angular-Komponente
import { Component, computed, inject } from '@angular/core';

// Werkzeuge für Navigation und die Anzeige untergeordneter Seiten
import {
  Router,
  RouterLink,
  RouterLinkActive,
  RouterOutlet
} from '@angular/router';

import { Auth } from '../../core/auth/auth';

@Component({
  selector: 'app-main-layout',

  // Diese Direktiven werden im HTML-Template verwendet
  imports: [RouterLink, RouterLinkActive, RouterOutlet],

  templateUrl: './main-layout.html',
  styleUrl: './main-layout.scss'
})
export class MainLayout {
  private readonly auth = inject(Auth);
  private readonly router = inject(Router);

  // Kommt garantiert nicht-null vor, solange authGuard diese Route schützt -
  // trotzdem als Signal durchgereicht statt einmalig kopiert, falls sich der
  // Nutzer künftig innerhalb derselben Session ändern könnte.
  protected readonly currentUser = this.auth.currentUser;

  // Initialen aus dem vollen Namen fürs Avatar, z.B. "Max Muster" -> "MM".
  protected readonly initials = computed(() => {
    const user = this.currentUser();
    if (!user) {
      return '';
    }
    return user.full_name
      .split(' ')
      .filter((part) => part.length > 0)
      .map((part) => part[0]!.toUpperCase())
      .slice(0, 2)
      .join('');
  });

  protected logout(): void {
    this.auth.logout().subscribe(() => this.router.navigateByUrl('/login'));
  }
}
