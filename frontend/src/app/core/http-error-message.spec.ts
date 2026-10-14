import { HttpErrorResponse } from '@angular/common/http';

import { errorMessageFor } from './http-error-message';

// Eine reine Funktion ohne Abhaengigkeiten - kein TestBed noetig, nur
// Eingabe rein, Ergebnis pruefen (wie die Backend-Tests fuer security.py).
describe('errorMessageFor', () => {
  const byStatus = { 409: 'Das Ticket wurde inzwischen geändert.' };
  const fallback = 'Aktion nicht möglich.';

  it('nimmt die passende Meldung fuer einen bekannten Statuscode', () => {
    const error = new HttpErrorResponse({ status: 409 });

    expect(errorMessageFor(error, byStatus, fallback)).toBe('Das Ticket wurde inzwischen geändert.');
  });

  it('meldet "Server nicht erreichbar", wenn gar keine Antwort kam (status 0)', () => {
    const error = new HttpErrorResponse({ status: 0 });

    expect(errorMessageFor(error, byStatus, fallback)).toContain('Server nicht erreichbar');
  });

  it('faellt fuer alle anderen Statuscodes auf die allgemeine Meldung zurueck', () => {
    const error = new HttpErrorResponse({ status: 500 });

    expect(errorMessageFor(error, byStatus, fallback)).toBe(fallback);
  });

  it('kommt auch mit Fehlern zurecht, die gar keine HTTP-Fehler sind', () => {
    expect(errorMessageFor(new Error('kaputt'), byStatus, fallback)).toBe(fallback);
  });
});
