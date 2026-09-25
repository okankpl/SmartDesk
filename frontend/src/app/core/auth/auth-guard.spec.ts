import { TestBed } from '@angular/core/testing';
import { Router, UrlTree } from '@angular/router';
import { provideRouter } from '@angular/router';

import { authGuard } from './auth-guard';
import { Auth } from './auth';

// authGuard ist eine reine Funktion (kein Klassenobjekt) und ruft intern
// inject(Auth)/inject(Router) auf - das funktioniert nur INNERHALB eines
// Angular-Injection-Kontexts. TestBed.runInInjectionContext(...) stellt genau
// diesen Kontext fuer den Dauer eines einzelnen Aufrufs bereit, ohne eine
// ganze Komponente drumherum bauen zu muessen.
describe('authGuard', () => {
  // Ein minimaler Test-Doppelgaenger (Stub) fuer Auth: nur das Signal, das
  // der Guard tatsaechlich liest, nichts von der echten HTTP-Logik - das
  // Ziel dieses Tests ist ausschliesslich die Guard-Entscheidung selbst.
  function configureWithLoginState(isLoggedIn: boolean): void {
    TestBed.configureTestingModule({
      providers: [provideRouter([]), { provide: Auth, useValue: { isLoggedIn: () => isLoggedIn } }],
    });
  }

  it('erlaubt den Zugriff, wenn eine gueltige Session besteht', () => {
    configureWithLoginState(true);

    const result = TestBed.runInInjectionContext(() => authGuard({} as never, {} as never));

    expect(result).toBe(true);
  });

  it('leitet auf /login um, wenn keine Session besteht', () => {
    configureWithLoginState(false);

    const result = TestBed.runInInjectionContext(() => authGuard({} as never, {} as never)) as UrlTree;

    // Ein UrlTree laesst sich nicht direkt mit einem String vergleichen -
    // ueber den echten Router (der intern denselben UrlTree-Typ nutzt)
    // zurueck in einen lesbaren Pfad-String uebersetzen.
    const router = TestBed.inject(Router);
    expect(router.serializeUrl(result)).toBe('/login');
  });
});
