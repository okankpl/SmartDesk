// HttpInterceptorFn ist der Funktions-Typ fuer einen "funktionalen"
// HTTP-Interceptor (die moderne Angular-Schreibweise, seit es dafuer keine
// eigene Klasse mit Decorator mehr braucht). Ein Interceptor haengt sich vor
// JEDE ausgehende HTTP-Anfrage - vergleichbar mit der CORS-Middleware im
// Backend (main.py), nur auf der Client- statt der Server-Seite.
import { HttpInterceptorFn } from '@angular/common/http';

// Ohne withCredentials wuerde der Browser den HttpOnly-Auth-Cookie bei
// Cross-Origin-Anfragen (4200 -> 8000) weder mitschicken noch einen neuen
// vom Server annehmen - unabhaengig davon, was CORS auf Backend-Seite erlaubt.
// Gilt fuer JEDE Anfrage an unser Backend, deshalb hier zentral statt pro Aufruf.
//
// Parameter: "req" ist die urspruengliche, unveraenderliche Anfrage; "next"
// ist eine Funktion, die die (ggf. veraenderte) Anfrage tatsaechlich abschickt
// und die Antwort zurueckgibt. req.clone({...}) erzeugt eine KOPIE der Anfrage
// mit zusaetzlichen/geaenderten Optionen - HttpRequest-Objekte selbst sind
// unveraenderlich (immutable), man kann sie nicht direkt bearbeiten.
export const credentialsInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req.clone({ withCredentials: true }));
};
