import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { API_URL } from '../api-url';
import { Ticket } from './ticket';

@Injectable({ providedIn: 'root' })
export class TicketsService {
  constructor(private readonly http: HttpClient) {}

  // Liefert nur die Tickets, die der eingeloggte Nutzer sehen darf - die
  // Sichtbarkeits-Filterung (Employee sieht nur eigene) passiert serverseitig
  // in list_tickets (tickets.py), nicht hier.
  list(): Observable<Ticket[]> {
    return this.http.get<Ticket[]>(`${API_URL}/tickets`);
  }
}
