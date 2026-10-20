import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { API_URL } from '../api-url';

// 1:1 wie DemoConfig im Backend (schemas/demo.py).
export interface DemoConfig {
  public_demo: boolean;
  registration_enabled: boolean;
  workspace_ttl_hours: number;
}

// Gilt, solange die echte Konfiguration noch nicht da ist oder nicht geladen
// werden konnte: keine oeffentliche Demo, Registrierung wie bisher sichtbar -
// also genau das Verhalten ohne diese Funktion.
export const DEFAULT_DEMO_CONFIG: DemoConfig = { public_demo: false, registration_enabled: true, workspace_ttl_hours: 24 };

@Injectable({ providedIn: 'root' })
export class DemoService {
  private readonly http = inject(HttpClient);

  // GET /demo/config ist ohne Anmeldung lesbar: die Anmeldeseite muss wissen,
  // ob sie "Demo starten" anbieten soll, bevor es eine Sitzung gibt.
  config(): Observable<DemoConfig> {
    return this.http.get<DemoConfig>(`${API_URL}/demo/config`);
  }
}
