import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { App } from './app';

// App ist nur eine duenne Huelle um <router-outlet /> (siehe app.html) - es
// gibt hier fachlich nichts Eigenes zu pruefen, nur dass die Komponente
// ueberhaupt fehlerfrei erzeugt werden kann. provideRouter([]) wird
// gebraucht, weil RouterOutlet (im "imports" von App) einen Router-Kontext
// erwartet, den TestBed sonst nicht bereitstellt.
describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter([])],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });
});
