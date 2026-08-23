import { HttpInterceptorFn } from '@angular/common/http';

// Ohne withCredentials wuerde der Browser den HttpOnly-Auth-Cookie bei
// Cross-Origin-Anfragen (4200 -> 8000) weder mitschicken noch einen neuen
// vom Server annehmen - unabhaengig davon, was CORS auf Backend-Seite erlaubt.
// Gilt fuer JEDE Anfrage an unser Backend, deshalb hier zentral statt pro Aufruf.
export const credentialsInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req.clone({ withCredentials: true }));
};
