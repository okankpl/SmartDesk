// Grundfunktion zum Erstellen einer Angular-Komponente
import { Component, computed, inject } from '@angular/core';

// Werkzeuge für Navigation und die Anzeige untergeordneter Seiten.
// RouterLink/RouterLinkActive werden fuer die Navigationslinks im Template
// gebraucht (routerLink="..." / routerLinkActive="active"). RouterOutlet ist
// der Platzhalter (<router-outlet />), an dem Angular die jeweils aktive
// Kind-Route einsetzt - hier also Dashboard oder TicketCreate, je nach URL
// (siehe app.routes.ts).
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
      // .split(' ') zerlegt "Max Muster" in ["Max", "Muster"].
      .split(' ')
      // .filter(...) wirft leere Eintraege raus (z.B. bei doppelten
      // Leerzeichen im Namen).
      .filter((part) => part.length > 0)
      // .map(...) ersetzt jedes Namensteil durch seinen ersten, grossgeschriebenen
      // Buchstaben - part[0]! (das "!" sagt TypeScript "das ist garantiert nicht
      // undefined", weil der vorherige filter()-Schritt leere Strings schon
      // ausgeschlossen hat).
      .map((part) => part[0]!.toUpperCase())
      // .slice(0, 2) nimmt hoechstens die ersten zwei Buchstaben (falls jemand
      // drei Vornamen hat, wollen wir trotzdem nur ein zweistelliges Kuerzel).
      .slice(0, 2)
      // .join('') fuegt die einzelnen Buchstaben wieder zu einem String zusammen,
      // z.B. ["M", "M"] -> "MM".
      .join('');
  });

  protected logout(): void {
    this.auth.logout().subscribe(() => this.router.navigateByUrl('/login'));
  }
}
