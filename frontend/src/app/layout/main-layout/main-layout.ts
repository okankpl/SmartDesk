// Grundfunktion zum Erstellen einer Angular-Komponente
import { Component } from '@angular/core';

// Werkzeuge für Navigation und die Anzeige untergeordneter Seiten
import {
  RouterLink,
  RouterLinkActive,
  RouterOutlet
} from '@angular/router';

@Component({
  selector: 'app-main-layout',

  // Diese Direktiven werden im HTML-Template verwendet
  imports: [RouterLink, RouterLinkActive, RouterOutlet],

  templateUrl: './main-layout.html',
  styleUrl: './main-layout.scss'
})
export class MainLayout {}
