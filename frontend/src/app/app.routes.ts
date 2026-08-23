// "Routes" ist der Typ fuer die Liste unten: ein Array von Regeln, die
// festlegen, welche Komponente Angular fuer welchen URL-Pfad anzeigt - das
// Frontend-Gegenstueck zu den @router.get(...)-Dekoratoren im Backend, nur
// dass hier URLs auf Komponenten statt auf Funktionen zeigen.
import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth-guard';
import { MainLayout } from './layout/main-layout/main-layout';
import { Dashboard } from './pages/dashboard/dashboard';
import { Login } from './pages/login/login';
import { TicketCreate } from './pages/ticket-create/ticket-create';

export const routes: Routes = [
  {
    path: 'login',
    component: Login,
    // "title" setzt automatisch den Browser-Tab-Titel, sobald diese Route
    // aktiv ist - kein manuelles document.title = "..." noetig.
    title: 'Anmelden | SmartDesk'
  },
  // Alle geschützten Anwendungsseiten werden innerhalb der App Shell angezeigt.
  // canActivate greift auf Ebene der Elternroute - ohne gültige Session leitet
  // authGuard direkt auf /login um, bevor irgendeine Kind-Route geladen wird.
  // "children" verschachtelt weitere Routen UNTER dieser URL: MainLayout
  // rendert seine <router-outlet /> (siehe main-layout.html), und je nach
  // restlichem Pfad (z.B. "dashboard") erscheint darin eine der Kind-Komponenten.
  {
    path: '',
    component: MainLayout,
    canActivate: [authGuard],
    children: [
      {
        // Leerer Pfad = genau die URL des Elternteils ("/") - pathMatch: 'full'
        // heisst "nur GENAU diese leere URL", nicht jede URL, die mit "/" anfaengt
        // (was sonst faelschlich auch "/dashboard" treffen wuerde).
        path: '',
        redirectTo: 'dashboard',
        pathMatch: 'full'
      },
      {
        path: 'dashboard',
        component: Dashboard,
        title: 'Dashboard | SmartDesk'
      },
      {
        path: 'tickets/new',
        component: TicketCreate,
        title: 'Neues Ticket | SmartDesk'
      }
    ]
  },
  // "**" ist ein Wildcard-Pfad: faengt JEDE URL, die von keiner Regel oben
  // getroffen wurde (z.B. Tippfehler in der Adresszeile). Muss deshalb die
  // letzte Regel in der Liste sein - Angular prueft der Reihe nach von oben.
  // Unbekannte Adressen führen zurück zum Dashboard
  {
    path: '**',
    redirectTo: 'dashboard'
  }
];
