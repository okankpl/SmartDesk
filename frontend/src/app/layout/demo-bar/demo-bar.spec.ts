import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router, provideRouter } from '@angular/router';

import { DemoBar } from './demo-bar';
import { Auth, CurrentUser } from '../../core/auth/auth';
import { API_URL } from '../../core/api-url';

const DEMO_EMPLOYEE: CurrentUser = {
  id: 51, email: 'employee.7@demo.smartdesk.invalid', full_name: 'Lena Fischer', role: 'employee',
  demo_expires_at: '2026-10-21T08:00:00Z',
};

describe('DemoBar', () => {
  beforeEach(() => TestBed.configureTestingModule({
    imports: [DemoBar],
    providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
  }));
  afterEach(() => TestBed.inject(HttpTestingController).verify());

  // Meldet ueber den echten Weg (/auth/me) an, wie in auth.spec.ts.
  function logIn(user: CurrentUser): void {
    TestBed.inject(Auth).refreshCurrentUser().subscribe();
    TestBed.inject(HttpTestingController).expectOne(`${API_URL}/auth/me`).flush(user);
  }

  function render(): HTMLElement {
    const fixture = TestBed.createComponent(DemoBar);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  it('zeigt bei normalen Konten nichts an', () => {
    logIn({ ...DEMO_EMPLOYEE, demo_expires_at: null });

    expect(render().querySelector('.demo-bar')).toBeNull();
  });

  it('zeigt im Demo-Arbeitsbereich Ablaufzeit und die aktive Rolle', () => {
    logIn(DEMO_EMPLOYEE);
    const root = render();

    expect(root.querySelector('.demo-bar')?.textContent).toContain('nur für dich sichtbar');
    const pressed = root.querySelector('button[aria-pressed="true"]');
    expect(pressed?.textContent?.trim()).toBe('Mitarbeitende');
  });

  it('wechselt die Rolle ueber das Backend und markiert danach die neue', () => {
    logIn(DEMO_EMPLOYEE);
    const fixture = TestBed.createComponent(DemoBar);
    fixture.detectChanges();
    const navigate = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    const root = fixture.nativeElement as HTMLElement;

    [...root.querySelectorAll('button')].find((button) => button.textContent?.includes('Support'))!.click();
    const request = TestBed.inject(HttpTestingController).expectOne(`${API_URL}/demo/sessions/role`);
    expect(request.request.body).toEqual({ role: 'agent' });
    request.flush({ ...DEMO_EMPLOYEE, id: 52, full_name: 'Alex Weber', role: 'agent' });
    fixture.detectChanges();

    expect(root.querySelector('button[aria-pressed="true"]')?.textContent?.trim()).toBe('Support');
    expect(navigate).toHaveBeenCalledWith('/dashboard');
  });
});
