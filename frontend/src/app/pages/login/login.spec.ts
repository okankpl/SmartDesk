import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';

import { Login } from './login';

// Baut die Login-Seite mit einer vorgegebenen URL-Abfrage (z.B.
// "?reason=session-expired"). Statt echter Navigation wird ActivatedRoute
// durch ein kleines Ersatz-Objekt mit genau dem Teil ersetzt, den Login
// liest (snapshot.queryParamMap). convertToParamMap macht aus einem
// einfachen Objekt dieselbe ParamMap, die der Router selbst liefern wuerde.
function createLogin(queryParams: Record<string, string>): HTMLElement {
  TestBed.configureTestingModule({
    imports: [Login],
    providers: [
      provideHttpClient(),
      provideHttpClientTesting(),
      provideRouter([]),
      { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(queryParams) } } },
    ],
  });
  const fixture = TestBed.createComponent(Login);
  fixture.detectChanges();
  return fixture.nativeElement as HTMLElement;
}

describe('Login', () => {
  it('zeigt einen Hinweis, wenn man wegen abgelaufener Sitzung umgeleitet wurde', () => {
    const root = createLogin({ reason: 'session-expired' });

    expect(root.querySelector('[role=status]')?.textContent).toContain('Sitzung ist abgelaufen');
  });

  it('zeigt keinen Hinweis bei einem normalen Aufruf der Login-Seite', () => {
    const root = createLogin({});

    expect(root.querySelector('[role=status]')).toBeNull();
  });
});
