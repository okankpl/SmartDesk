import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { MainLayout } from './main-layout';

// MainLayout haengt (ueber inject(Auth)) transitiv an HttpClient und
// (ueber RouterLink im Template) an einem Router-Kontext - beides muss
// TestBed hier bereitstellen, sonst schlaegt schon das reine Erzeugen der
// Komponente mit einem Dependency-Injection-Fehler fehl (genau das ist vor
// diesem Fix passiert: NG0201 "No provider found for ActivatedRoute").
// provideHttpClientTesting() ersetzt den echten HTTP-Backend-Aufruf durch
// eine Test-Version, die NICHTS ins echte Netzwerk schickt - ohne das wuerde
// dieser Test versuchen, wirklich http://localhost:8000/auth/me aufzurufen.
describe('MainLayout', () => {
  let component: MainLayout;
  let fixture: ComponentFixture<MainLayout>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MainLayout],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(MainLayout);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
