import { TestBed, ComponentFixture } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { Register } from './register';
import { API_URL } from '../../core/api-url';

describe('Register', () => {
  let fixture: ComponentFixture<Register>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Register], providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();
    fixture = TestBed.createComponent(Register);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });
  afterEach(() => http.verify());

  function submit(password = 'test-password', confirmation = password): void {
    const form = (fixture.nativeElement as HTMLElement).querySelector('form')!;
    for (const [name, value] of Object.entries({ full_name: 'Lena Fischer', email: 'lena@example.com', password, confirmation })) {
      form.querySelector<HTMLInputElement>(`[name="${name}"]`)!.value = value;
    }
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    fixture.detectChanges();
  }

  it('rejects mismatched passwords without a request', () => {
    submit('test-password', 'different-password');
    expect(fixture.nativeElement.textContent).toContain('stimmen nicht überein');
    http.expectNone(`${API_URL}/auth/register`);
  });

  it('checks the bcrypt byte limit for unicode passwords', () => {
    submit('ü'.repeat(40));
    expect(fixture.nativeElement.textContent).toContain('72 Bytes');
    http.expectNone(`${API_URL}/auth/register`);
  });

  it('registers without a role and navigates to login on success', () => {
    const navigate = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
    submit();
    const request = http.expectOne(`${API_URL}/auth/register`);
    expect(request.request.body).toEqual({ full_name: 'Lena Fischer', email: 'lena@example.com', password: 'test-password' });
    request.flush({ id: 1, full_name: 'Lena Fischer', email: 'lena@example.com', role: 'employee' });
    expect(navigate).toHaveBeenCalledWith(['/login'], { queryParams: { registered: '1' } });
  });

  it('explains duplicate accounts and preserves form input', () => {
    submit();
    http.expectOne(`${API_URL}/auth/register`).flush({}, { status: 409, statusText: 'Conflict' });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('bereits registriert');
    expect(fixture.nativeElement.querySelector('[name="email"]').value).toBe('lena@example.com');
    expect(fixture.nativeElement.querySelector('button[type="submit"]').disabled).toBe(false);
  });
});
