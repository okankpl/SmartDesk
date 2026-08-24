// Einzige Quelle fuer die Backend-Basis-URL, damit sie nicht in jedem Service
// separat hartcodiert ist (DRY - siehe get_settings() im Backend fuer denselben
// Gedanken).
//
// Der Wert selbst kommt aus environment.ts (lokal: volle URL zum separat
// laufenden Backend) bzw. environment.prod.ts (Produktion: relativer Pfad,
// da Frontend+Backend dort hinter derselben Domain liegen - siehe die
// Kommentare in environment.prod.ts und docs/deployment.md). Angular tauscht
// die Datei automatisch aus, siehe "fileReplacements" in angular.json.
import { environment } from '../../environments/environment';

export const API_URL = environment.apiUrl;
