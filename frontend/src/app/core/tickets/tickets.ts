import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { API_URL } from '../api-url';
import { Ticket, TicketPriority } from './ticket';

// Nur die Felder, die der Client beim Erstellen wirklich mitgeben darf - kein
// status (startet immer auf "open", serverseitig per Default), kein
// requester_id (kommt aus dem eingeloggten Nutzer, siehe TicketCreate-Schema
// im Backend - derselbe Mass-Assignment-Gedanke wie beim Login).
export interface NewTicket {
  title: string;
  description: string | null;
  priority: TicketPriority;
}

@Injectable({ providedIn: 'root' })
export class TicketsService {
  constructor(private readonly http: HttpClient) {}

  // Liefert nur die Tickets, die der eingeloggte Nutzer sehen darf - die
  // Sichtbarkeits-Filterung (Employee sieht nur eigene) passiert serverseitig
  // in list_tickets (tickets.py), nicht hier.
  list(): Observable<Ticket[]> {
    return this.http.get<Ticket[]>(`${API_URL}/tickets`);
  }

  create(newTicket: NewTicket): Observable<Ticket> {
    return this.http.post<Ticket>(`${API_URL}/tickets`, newTicket);
  }
}
