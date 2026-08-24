// Wird fuer lokale Entwicklung genutzt (ng serve / ng build ohne --configuration
// production). Backend laeuft lokal auf einem anderen Port (8000) als das
// Frontend (4200) - deshalb eine volle, absolute URL noetig.
export const environment = {
  apiUrl: 'http://localhost:8000',
};
