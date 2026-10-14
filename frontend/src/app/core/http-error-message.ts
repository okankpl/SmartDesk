// HttpErrorResponse ist die Klasse, in die HttpClient jede fehlgeschlagene
// Antwort verpackt - .status enthaelt den HTTP-Statuscode.
import { HttpErrorResponse } from '@angular/common/http';

// status 0 heisst bei HttpClient: es kam GAR KEINE HTTP-Antwort an (Backend
// aus, Netzwerk weg, Anfrage vom Browser blockiert) - das ist ueberall
// dieselbe Situation, deshalb dieselbe Meldung.
const SERVER_UNREACHABLE = 'Server nicht erreichbar. Bitte Verbindung prüfen und erneut versuchen.';

/**
 * Waehlt eine verstaendliche Fehlermeldung fuer eine fehlgeschlagene Anfrage.
 *
 * Vorher zeigte jede Komponente bei JEDEM Fehler dieselbe feste Meldung - die
 * Login-Seite etwa "E-Mail oder Passwort ist falsch", auch wenn in Wahrheit
 * der Server nicht lief. Bewusst NICHT der rohe "detail"-Text aus dem Backend:
 * der ist fuer Entwickler formuliert (z.B. "Übergang von 'resolved' zu
 * 'closed' ist nicht erlaubt") und kann sich aendern, ohne dass jemand an die
 * Oberflaeche denkt.
 *
 * @param error    der Fehler aus dem error-Callback von subscribe()
 * @param byStatus Meldungen fuer Statuscodes, die an DIESER Stelle eine
 *                 besondere Bedeutung haben (z.B. 409 beim Statuswechsel).
 *                 Partial<Record<number, string>> heisst: ein Objekt mit
 *                 Zahlen als Schluessel und Texten als Werten, in dem jeder
 *                 Eintrag optional ist.
 * @param fallback Meldung fuer alle anderen Faelle
 */
export function errorMessageFor(error: unknown, byStatus: Partial<Record<number, string>>, fallback: string): string {
  if (error instanceof HttpErrorResponse) {
    if (error.status === 0) {
      return SERVER_UNREACHABLE;
    }
    // ?? fallback: gibt es fuer diesen Statuscode keinen eigenen Eintrag
    // (undefined), gilt die allgemeine Meldung.
    return byStatus[error.status] ?? fallback;
  }
  return fallback;
}
