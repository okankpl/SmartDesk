import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { API_URL } from '../api-url';
import { TicketComment } from './comment';

// Gleicher Aufbau wie TicketsService (core/tickets/tickets.ts): ein Singleton
// (providedIn: 'root'), der nur HTTP-Aufrufe kapselt und selbst keinen
// Zustand haelt - welche Kommentare gerade angezeigt werden, verwaltet die
// Komponente (ticket-card.ts), nicht dieser Service.
@Injectable({ providedIn: 'root' })
export class CommentsService {
  constructor(private readonly http: HttpClient) {}

  // GET /tickets/{id}/comments - liefert die Kommentare bereits chronologisch
  // sortiert (aelteste zuerst), das Sortieren passiert serverseitig in
  // list_comments (routers/comments.py), nicht hier.
  list(ticketId: number): Observable<TicketComment[]> {
    return this.http.get<TicketComment[]>(`${API_URL}/tickets/${ticketId}/comments`);
  }

  // POST /tickets/{id}/comments. Der Request-Body enthaelt bewusst NUR den
  // Text: ticket_id steckt schon in der URL, author_id bestimmt das Backend
  // selbst aus dem eingeloggten Nutzer (Mass-Assignment-Schutz, siehe
  // CommentCreate in schemas/comment.py). { body } ist JavaScript-Kurzschreib-
  // weise fuer { body: body } - Objekt-Feld und Variable heissen gleich.
  create(ticketId: number, body: string): Observable<TicketComment> {
    return this.http.post<TicketComment>(`${API_URL}/tickets/${ticketId}/comments`, { body });
  }
}
