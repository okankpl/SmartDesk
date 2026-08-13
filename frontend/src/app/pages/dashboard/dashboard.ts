// Importiert die Werkzeuge für Komponenten und reaktive Daten
import { Component, signal } from '@angular/core';

@Component({
  selector: 'app-dashboard', // HTML-Name der Komponente
  imports: [], // Weitere benötigte Komponenten und Direktiven
  templateUrl: './dashboard.html', // Zugehöriges HTML-Template
  styleUrl: './dashboard.scss' // Styles nur für diese Komponente
})
export class Dashboard {
  // Reaktiver Zustand mit dem Startwert 12
  protected readonly openTickets = signal(12);
}
