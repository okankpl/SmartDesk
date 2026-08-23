import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth-guard';
import { MainLayout } from './layout/main-layout/main-layout';
import { Dashboard } from './pages/dashboard/dashboard';
import { Login } from './pages/login/login';

export const routes: Routes = [
  {
    path: 'login',
    component: Login,
    title: 'Anmelden | SmartDesk'
  },
  // Alle geschützten Anwendungsseiten werden innerhalb der App Shell angezeigt.
  // canActivate greift auf Ebene der Elternroute - ohne gültige Session leitet
  // authGuard direkt auf /login um, bevor irgendeine Kind-Route geladen wird.
  {
    path: '',
    component: MainLayout,
    canActivate: [authGuard],
    children: [
      {
        path: '',
        redirectTo: 'dashboard',
        pathMatch: 'full'
      },
      {
        path: 'dashboard',
        component: Dashboard,
        title: 'Dashboard | SmartDesk'
      }
    ]
  },
  // Unbekannte Adressen führen zurück zum Dashboard
  {
    path: '**',
    redirectTo: 'dashboard'
  }
];
