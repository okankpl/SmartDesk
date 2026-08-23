// Einzige Quelle fuer die Backend-Basis-URL, damit sie nicht in jedem Service
// separat hartcodiert ist (DRY - siehe get_settings() im Backend fuer denselben
// Gedanken).
// TODO: aus einer Umgebungskonfiguration lesen, sobald es ein echtes Deployment
// gibt (siehe "Bewusste Einschraenkungen" in der Architektur-Doku - dieselbe
// Vereinfachung steht dort schon fuer die CORS-Origin im Backend).
export const API_URL = 'http://localhost:8000';
