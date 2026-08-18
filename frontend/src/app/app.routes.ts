import { Routes } from '@angular/router';
import { MainLayout } from './layout/main-layout/main-layout';
import { Dashboard } from './pages/dashboard/dashboard';

export const routes: Routes = [
  // Alle geschützten Anwendungsseiten werden innerhalb der App Shell angezeigt
  {
    path: '',
    component: MainLayout,
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
