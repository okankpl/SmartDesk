// Ersetzt environment.ts bei "ng build --configuration production" (siehe
// "fileReplacements" in angular.json). In Produktion laufen Frontend und
// Backend HINTER DEMSELBEN Domain-Namen (Caddy leitet /api/* zum Backend
// weiter, siehe docs/deployment.md) - deshalb reicht ein relativer Pfad statt
// einer vollen URL. Das macht Frontend und Backend zu derselben "Origin" aus
// Browser-Sicht: kein CORS noetig, der Auth-Cookie ist automatisch "same-site".
export const environment = {
  apiUrl: '/api',
};
