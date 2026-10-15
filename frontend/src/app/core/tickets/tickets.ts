import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { API_URL } from '../api-url';
import { Ticket, TicketPriority, TicketStatus } from './ticket';
import { TicketEvent } from './ticket-event';

// Nur die Felder, die der Client beim Erstellen wirklich mitgeben darf - kein
// status (startet immer auf "open", serverseitig per Default), kein
// requester_id (kommt aus dem eingeloggten Nutzer, siehe TicketCreate-Schema
// im Backend - derselbe Mass-Assignment-Gedanke wie beim Login).
export interface NewTicket {
  title: string;
  description: string | null;
  priority: TicketPriority;
}

export interface TicketContentUpdate extends Partial<NewTicket> {
  expected_version: number;
}

// providedIn: 'root' -> eine einzige, geteilte Instanz fuer die ganze App
// (Singleton), siehe ausfuehrlichere Erklaerung dazu in core/auth/auth.ts.
@Injectable({ providedIn: 'root' })
export class TicketsService {
  constructor(private readonly http: HttpClient) {}

  // http.get<Ticket[]>(...) heisst: "mach eine GET-Anfrage, und wenn die
  // Antwort ankommt, behandle das JSON als Ticket[]" - das ist reine
  // TypeScript-Typisierung (Compile-Zeit), keine echte Laufzeit-Pruefung, ob
  // das Backend tatsaechlich so ein Array liefert (siehe Kommentar zu diesem
  // Unterschied in ticket.ts).
  //
  // Liefert nur die Tickets, die der eingeloggte Nutzer sehen darf - die
  // Sichtbarkeits-Filterung (Employee sieht nur eigene) passiert serverseitig
  // in list_tickets (tickets.py), nicht hier.
  list(): Observable<Ticket[]> {
    return this.http.get<Ticket[]>(`${API_URL}/tickets`);
  }

  // Der Rueckgabewert ist ein Observable<Ticket> statt sofort ein Ticket, weil
  // eine HTTP-Anfrage asynchron ist (dauert Zeit, laeuft ueber das Netzwerk) -
  // der Aufrufer (siehe ticket-create.ts) muss sich per .subscribe(...) "dafuer
  // anmelden", benachrichtigt zu werden, sobald die Antwort da ist.
  create(newTicket: NewTicket): Observable<Ticket> {
    return this.http.post<Ticket>(`${API_URL}/tickets`, newTicket);
  }

  get(ticketId: number): Observable<Ticket> {
    return this.http.get<Ticket>(`${API_URL}/tickets/${ticketId}`);
  }

  updateContent(ticketId: number, changes: TicketContentUpdate): Observable<Ticket> {
    return this.http.patch<Ticket>(`${API_URL}/tickets/${ticketId}`, changes);
  }

  // Ruft PATCH /tickets/{id}/status auf. Ob dieser Aufruf ueberhaupt Sinn
  // ergibt (also ob newStatus in ticket.allowed_transitions steht), prueft
  // NICHT dieser Service - das entscheidet die aufrufende Komponente anhand
  // der vom Backend gelieferten allowed_transitions (siehe ticket-card.ts).
  updateStatus(ticketId: number, newStatus: TicketStatus): Observable<Ticket> {
    return this.http.patch<Ticket>(`${API_URL}/tickets/${ticketId}/status`, { status: newStatus });
  }

  history(ticketId: number): Observable<TicketEvent[]> {
    return this.http.get<TicketEvent[]>(`${API_URL}/tickets/${ticketId}/history`);
  }

  assign(ticketId: number, assigneeId: number | null, expectedVersion: number): Observable<Ticket> {
    return this.http.patch<Ticket>(`${API_URL}/tickets/${ticketId}`, { assignee_id: assigneeId, expected_version: expectedVersion });
  }
}
