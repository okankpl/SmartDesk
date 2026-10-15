import { test, expect, Page } from '@playwright/test';
import path from 'node:path';

const password = 'SmartDesk-Demo26!';

async function login(page: Page, role: 'employee' | 'agent' | 'admin'): Promise<void> {
  await page.goto('/login');
  await page.getByLabel('E-Mail', { exact: true }).fill(`${role}@example.com`);
  await page.getByLabel('Passwort', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Anmelden', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Dashboard', exact: true })).toBeVisible();
  await expect(page.locator('.stat-grid')).toBeVisible();
}

async function view(page: Page, label: string): Promise<void> {
  await page.locator('.view-tabs__button').filter({ hasText: label }).click();
}

async function openTicket(page: Page, title: string): Promise<void> {
  await page.locator('.ticket-card__trigger').filter({ hasText: title }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
}

test('demo queue, filters, named comments and responsive ticket details', async ({ page, isMobile }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await login(page, 'agent');
  await expect(page.locator('.ticket-card')).toHaveCount(5);
  if (process.env['UPDATE_SCREENSHOTS']) {
    await page.mouse.move(0, 0);
    await page.screenshot({ path: path.resolve(isMobile ? '../docs/images/mobile.png' : '../docs/images/dashboard.png'), fullPage: true });
  }
  await page.getByRole('searchbox').fill('VPN');
  await page.getByLabel('Priorität', { exact: true }).selectOption('critical');
  await expect(page.locator('.ticket-card')).toHaveCount(1);
  await page.getByRole('button', { name: 'Zurücksetzen', exact: true }).click();
  await openTicket(page, 'VPN-Verbindung bricht im Homeoffice ab');
  await expect(page.getByRole('dialog')).toContainText('Lena Fischer');
  await expect(page.getByRole('dialog')).toContainText('Ticket erstellt');
  if (process.env['UPDATE_SCREENSHOTS'] && !isMobile) {
    await page.screenshot({ path: path.resolve('../docs/images/ticket-detail.png') });
    await page.getByRole('dialog').getByRole('button', { name: 'Ticket bearbeiten', exact: true }).click();
    await page.screenshot({ path: path.resolve('../docs/images/ticket-editor.png') });
    await page.getByRole('dialog').getByRole('button', { name: 'Abbrechen', exact: true }).click();
  }
  const size = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth }));
  expect(size.scroll).toBeLessThanOrEqual(size.width);
  const dialog = await page.getByRole('dialog').boundingBox();
  expect(dialog!.x).toBeGreaterThanOrEqual(0);
  expect(dialog!.x + dialog!.width).toBeLessThanOrEqual(size.width);
  await page.getByRole('button', { name: 'Schließen', exact: true }).click();
  expect(errors).toEqual([]);
});

test('login throttling preserves inputs and permits retry after the cooldown', async ({ page }, testInfo) => {
  let intercepted = false;
  await page.route('**/api/auth/login', async route => {
    if (intercepted) return route.continue();
    intercepted = true;
    await route.fulfill({ status: 429, contentType: 'application/json',
      headers: { 'Retry-After': '2' }, body: JSON.stringify({ detail: 'Zu viele Anmeldeversuche' }) });
  });
  await page.goto('/login');
  await page.getByLabel('E-Mail', { exact: true }).fill('agent@example.com');
  await page.getByLabel('Passwort', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Anmelden', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Zu viele Anmeldeversuche');
  await expect(page.locator('button[type=submit]')).toBeDisabled();
  await expect(page.getByLabel('E-Mail', { exact: true })).toHaveValue('agent@example.com');
  await expect(page.getByLabel('Passwort', { exact: true })).toHaveValue(password);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(await page.evaluate(() => innerWidth));
  await page.screenshot({ path: path.resolve(`../tmp/login-throttle-${testInfo.project.name}.png`) });
  await expect(page.getByRole('button', { name: 'Anmelden', exact: true })).toBeEnabled({ timeout: 5000 });
  await page.getByRole('button', { name: 'Anmelden', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Dashboard', exact: true })).toBeVisible();
});

test('employee creates and comments, agent claims and resolves, admin closes', async ({ page }, testInfo) => {
  const title = `E2E ${testInfo.project.name} ${Date.now()}`;
  let ticketId: number | undefined;
  try {
    await login(page, 'employee');
    await page.locator('.new-ticket-button').click();
    await page.getByLabel('Titel', { exact: true }).fill(title);
    await page.getByLabel('Beschreibung (optional)').fill('Automatisierter Browser-Test des vollständigen Support-Ablaufs.');
    await page.getByLabel('Priorität', { exact: true }).selectOption('high');
    const created = page.waitForResponse(response => response.url().endsWith('/api/tickets') && response.request().method() === 'POST');
    await page.getByRole('button', { name: 'Ticket anlegen', exact: true }).click();
    ticketId = (await (await created).json()).id;
    await expect(page.locator('.dashboard > .notice[role=status]')).toContainText('wurde erstellt');
    await openTicket(page, title);
    await expect(page.getByRole('button', { name: 'Übernehmen', exact: true })).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Ticket bearbeiten', exact: true })).toHaveCount(0);
    await page.getByRole('textbox', { name: 'Neuer Kommentar' }).fill('Der Fehler tritt seit heute auf.');
    await page.getByRole('button', { name: 'Kommentar senden', exact: true }).click();
    await expect(page.locator('.ticket-comments__body').last()).toHaveText('Der Fehler tritt seit heute auf.');
    await page.getByRole('button', { name: 'Schließen', exact: true }).click();
    await page.getByRole('button', { name: 'Abmelden' }).click();

    await login(page, 'agent');
    await openTicket(page, title);
    await page.getByRole('textbox', { name: 'Neuer Kommentar' }).fill('Entwurf für die nächste Rückfrage');
    await page.getByRole('button', { name: 'Übernehmen', exact: true }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByRole('dialog').locator('.detail-notice[role=status]')).toContainText('In Bearbeitung');
    await expect(page.getByRole('textbox', { name: 'Neuer Kommentar' })).toHaveValue('Entwurf für die nächste Rückfrage');
    await page.getByRole('button', { name: 'Schließen', exact: true }).click();
    await expect(page.getByRole('dialog')).not.toBeVisible();
    await view(page, 'In Bearbeitung');
    await openTicket(page, title);
    await expect(page.getByRole('dialog')).toContainText('Alex Weber');
    await page.getByRole('button', { name: 'Als gelöst markieren', exact: true }).click();
    await expect(page.getByRole('dialog').locator('.detail-notice[role=status]')).toContainText('Gelöst');
    await page.getByRole('button', { name: 'Schließen', exact: true }).click();
    await expect(page.getByRole('dialog')).not.toBeVisible();
    await page.getByRole('button', { name: 'Abmelden' }).click();

    await login(page, 'admin');
    await view(page, 'Gelöste Tickets');
    await openTicket(page, title);
    await page.locator('.ticket-detail__actions').getByRole('button', { name: 'Schließen', exact: true }).click();
    await expect(page.getByRole('dialog').locator('.detail-notice[role=status]')).toContainText('Geschlossen');
    await page.getByRole('button', { name: 'Schließen', exact: true }).click();
    await expect(page.getByRole('dialog')).not.toBeVisible();
    await view(page, 'Geschlossene Tickets');
    await openTicket(page, title);
    await expect(page.locator('app-ticket-history')).toContainText('Geschlossen');
    await expect(page.locator('app-ticket-history')).toContainText('Samira Kaya');
    await expect(page.locator('.ticket-detail__action')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Ticket bearbeiten', exact: true })).toHaveCount(0);
  } finally {
    testInfo.setTimeout(testInfo.timeout + 10_000);
    if (ticketId) {
      const auth = await page.request.post('/api/auth/login', { form: { username: 'admin@example.com', password } });
      expect(auth.ok()).toBeTruthy();
      const deleted = await page.request.delete(`/api/tickets/${ticketId}`);
      expect(deleted.status()).toBe(204);
    }
  }
});

test('admin assigns support staff and the change is recorded', async ({ page }, testInfo) => {
  await login(page, 'admin');
  const title = `Assignment ${testInfo.project.name} ${Date.now()}`;
  const created = await page.request.post('/api/tickets', { data: { title, priority: 'medium' } });
  expect(created.status()).toBe(201);
  const ticketId = (await created.json()).id;
  try {
    await page.reload();
    await openTicket(page, title);
    const select = page.getByRole('dialog').getByRole('combobox');
    await expect(select).toBeEnabled();
    await expect(select.locator('option')).toHaveCount(3);
    await select.selectOption({ label: 'Alex Weber' });
    await page.getByRole('button', { name: 'Zuweisen', exact: true }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByRole('dialog').locator('.detail-notice[role=status]')).toContainText('Bearbeiter wurde aktualisiert');
    await expect(page.getByRole('dialog').locator('.ticket-detail__meta')).toContainText('Alex Weber');
    await expect(page.locator('app-ticket-history')).toContainText('Ticket geändert');
    await expect(page.locator('app-ticket-history')).toContainText('Samira Kaya');
  } finally {
    testInfo.setTimeout(testInfo.timeout + 10_000);
    expect((await page.request.delete(`/api/tickets/${ticketId}`)).status()).toBe(204);
  }
});

test('registration creates an employee account and login works', async ({ page }, testInfo) => {
  const email = `browser-${testInfo.project.name}-${Date.now()}@example.com`;
  await page.goto('/register');
  await page.getByLabel('Vollständiger Name').fill('Portfolio Test');
  await page.getByLabel('E-Mail', { exact: true }).fill(email);
  await page.getByLabel('Passwort', { exact: true }).fill('Registration-Test26!');
  await page.getByLabel('Passwort wiederholen').fill('Registration-Test26!');
  await page.getByRole('button', { name: 'Konto erstellen', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('Konto wurde erstellt');
  await page.getByLabel('E-Mail', { exact: true }).fill(email);
  await page.getByLabel('Passwort', { exact: true }).fill('Registration-Test26!');
  await page.getByRole('button', { name: 'Anmelden', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  await expect(page.locator('.ticket-card')).toHaveCount(0);
  const profile = await page.request.get('/api/auth/me');
  expect((await profile.json()).role).toBe('employee');
});

test('list and cards, cross-status search, sorting and keyboard access', async ({ page }) => {
  await login(page, 'agent');
  await expect(page.locator('.ticket-grid')).toHaveClass(/ticket-grid--list/);
  await page.getByRole('button', { name: 'Kartenansicht', exact: true }).click();
  await expect(page.locator('.ticket-grid')).not.toHaveClass(/ticket-grid--list/);
  await page.getByRole('button', { name: 'Listenansicht', exact: true }).click();
  await view(page, 'Geschlossene Tickets');
  await page.getByRole('searchbox').fill('VPN');
  await expect(page.getByRole('heading', { name: 'Keine passenden Tickets' })).toBeVisible();
  await view(page, 'Alle Tickets');
  await expect(page.locator('.ticket-card')).toHaveCount(1);
  await page.getByRole('button', { name: 'Suche löschen', exact: true }).click();
  const data = await (await page.request.get('/api/tickets')).json();
  await page.getByLabel('Sortierung', { exact: true }).selectOption('newest');
  const newest = [...data].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at) || b.id - a.id)[0];
  await expect(page.locator('.ticket-card__title').first()).toHaveText(newest.title);
  const trigger = page.locator('.ticket-card__trigger').first();
  await trigger.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).not.toBeVisible();
  await expect(trigger).toBeFocused();
});

test('long ticket content stays within narrow, tablet and wide layouts', async ({ page }, testInfo) => {
  await login(page, 'admin');
  const title = `Layout ${testInfo.project.name} ${Date.now()} ${'LangerTitel'.repeat(14)}`;
  const created = await page.request.post('/api/tickets', {
    data: { title, priority: 'critical', description: 'Ein langer Beschreibungstext ohne Datenverlust.\n'.repeat(100) },
  });
  expect(created.status()).toBe(201);
  const ticketId = (await created.json()).id;
  try {
    await page.reload();
    for (const width of [320, 768, 1440]) {
      await page.setViewportSize({ width, height: 900 });
      await expect(page.locator('.ticket-card__title').filter({ hasText: title })).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
      await openTicket(page, title);
      const dialog = page.getByRole('dialog');
      const bounds = await dialog.boundingBox();
      expect(bounds!.x).toBeGreaterThanOrEqual(0);
      expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(width);
      const footer = await dialog.locator('.ticket-detail__footer').boundingBox();
      const header = await dialog.locator('.ticket-detail__header').boundingBox();
      expect(footer!.y).toBeGreaterThan(header!.y + header!.height);
      expect(footer!.y + footer!.height).toBeLessThanOrEqual(900);
      expect(await dialog.evaluate(element => element.scrollWidth <= element.clientWidth)).toBeTruthy();
      await dialog.locator('.ticket-detail__body').evaluate(element => { element.scrollTop = element.scrollHeight; });
      await expect(dialog.getByRole('button', { name: 'Übernehmen', exact: true })).toBeInViewport();
      await dialog.getByRole('button', { name: 'Ticket bearbeiten', exact: true }).click();
      await expect(dialog.getByLabel('Titel', { exact: true })).toHaveValue(title);
      expect(await dialog.evaluate(element => element.scrollWidth <= element.clientWidth)).toBeTruthy();
      await expect(dialog.getByRole('button', { name: 'Speichern', exact: true })).toBeInViewport();
      await dialog.getByRole('button', { name: 'Abbrechen', exact: true }).click();
      await dialog.getByRole('button', { name: 'Schließen', exact: true }).click();
    }
    await page.setViewportSize({ width: 320, height: 900 });
    await page.locator('.new-ticket-button').click();
    await page.getByLabel('Titel', { exact: true }).fill(title);
    await page.getByLabel('Beschreibung (optional)').fill('Mehrzeiliger Entwurf\nmit vollständigen Angaben.');
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
    await expect(page.getByRole('button', { name: 'Ticket anlegen', exact: true })).toBeVisible();
  } finally {
    testInfo.setTimeout(testInfo.timeout + 10_000);
    expect((await page.request.delete(`/api/tickets/${ticketId}`)).status()).toBe(204);
  }
});

test('support edits content, keeps comment drafts and explicitly discards unsaved changes', async ({ page }, testInfo) => {
  await login(page, 'agent');
  const title = `Edit ${testInfo.project.name} ${Date.now()}`;
  const created = await page.request.post('/api/tickets', { data: { title, priority: 'medium', description: 'Ausgangsbeschreibung' } });
  expect(created.status()).toBe(201);
  const ticketId = (await created.json()).id;
  try {
    await page.reload();
    await openTicket(page, title);
    const dialog = page.getByRole('dialog');
    const comment = dialog.getByRole('textbox', { name: 'Neuer Kommentar' });
    await comment.fill('Kommentarentwurf bleibt bestehen');
    await dialog.getByRole('button', { name: 'Ticket bearbeiten', exact: true }).click();
    await expect(dialog.getByLabel('Titel', { exact: true })).toBeFocused();
    await expect(dialog.getByRole('button', { name: 'Speichern', exact: true })).toBeDisabled();
    await dialog.getByLabel('Titel', { exact: true }).fill(`${title} bearbeitet`);
    await dialog.getByLabel('Beschreibung (optional)').fill('Ergänzte Diagnose mit konkreten Schritten.');
    await dialog.getByLabel('Priorität', { exact: true }).selectOption('critical');
    await dialog.getByRole('button', { name: 'Speichern', exact: true }).click();
    await expect(dialog.locator('h2')).toHaveText(`${title} bearbeitet`);
    await expect(dialog.locator('.detail-notice')).toContainText('Ticketänderungen wurden gespeichert');
    await expect(dialog.locator('.ticket-detail__sidebar')).toContainText('Kritisch');
    await expect(comment).toHaveValue('Kommentarentwurf bleibt bestehen');
    await expect(dialog.locator('app-ticket-history')).toContainText('Ergänzte Diagnose');
    await expect(dialog.getByRole('button', { name: 'Ticket bearbeiten', exact: true })).toBeFocused();
    await dialog.getByRole('button', { name: 'Ticket bearbeiten', exact: true }).click();
    await dialog.getByLabel('Titel', { exact: true }).fill('Nicht gespeicherter Entwurf');
    await page.keyboard.press('Escape');
    await expect(dialog.locator('.discard-confirm')).toContainText('Ungespeicherte Änderungen');
    await dialog.getByRole('button', { name: 'Weiter bearbeiten', exact: true }).click();
    await expect(dialog.getByLabel('Titel', { exact: true })).toHaveValue('Nicht gespeicherter Entwurf');
    await dialog.getByRole('button', { name: 'Abbrechen', exact: true }).click();
    await dialog.getByRole('button', { name: 'Änderungen verwerfen', exact: true }).click();
    await expect(dialog.locator('app-ticket-editor')).toHaveCount(0);
    await expect(dialog).toBeVisible();
    await expect(dialog.locator('h2')).toHaveText(`${title} bearbeitet`);
    await expect(comment).toHaveValue('Kommentarentwurf bleibt bestehen');
    await dialog.getByRole('button', { name: 'Schließen', exact: true }).click();
    await expect(page.locator('.ticket-card__title').filter({ hasText: `${title} bearbeitet` })).toBeVisible();
    const stored = await (await page.request.get(`/api/tickets/${ticketId}`)).json();
    expect(stored.version).toBe(2);
    expect(stored.description).toBe('Ergänzte Diagnose mit konkreten Schritten.');
  } finally {
    testInfo.setTimeout(testInfo.timeout + 10_000);
    await page.request.post('/api/auth/login', { form: { username: 'admin@example.com', password } });
    expect((await page.request.delete(`/api/tickets/${ticketId}`)).status()).toBe(204);
  }
});

test('a conflicting edit preserves the draft and reloads before retrying', async ({ page }, testInfo) => {
  await login(page, 'agent');
  const title = `Conflict ${testInfo.project.name} ${Date.now()}`;
  const created = await page.request.post('/api/tickets', { data: { title, priority: 'medium' } });
  expect(created.status()).toBe(201);
  const ticket = await created.json();
  const path = `/api/tickets/${ticket.id}`;
  try {
    await page.reload();
    await openTicket(page, title);
    const dialog = page.getByRole('dialog');
    await dialog.getByRole('button', { name: 'Ticket bearbeiten', exact: true }).click();
    await dialog.getByLabel('Titel', { exact: true }).fill(`${title} lokaler Entwurf`);
    const remote = await page.request.patch(path, { data: { title: `${title} anderer Stand`, expected_version: ticket.version } });
    expect(remote.status()).toBe(200);
    const conflict = page.waitForResponse(response => response.url().endsWith(path) && response.request().method() === 'PATCH');
    await dialog.getByRole('button', { name: 'Speichern', exact: true }).click();
    expect((await conflict).status()).toBe(409);
    await expect(dialog.locator('app-ticket-editor [role=alert]')).toContainText('Entwurf wurde nicht gespeichert');
    await expect(dialog.getByLabel('Titel', { exact: true })).toHaveValue(`${title} lokaler Entwurf`);
    await expect(dialog.getByRole('button', { name: 'Speichern', exact: true })).toBeDisabled();
    expect((await (await page.request.get(path)).json()).title).toBe(`${title} anderer Stand`);
    await dialog.getByRole('button', { name: 'Entwurf verwerfen und neu laden', exact: true }).click();
    await expect(dialog.getByLabel('Titel', { exact: true })).toHaveValue(`${title} anderer Stand`);
    await dialog.getByLabel('Titel', { exact: true }).fill(`${title} zusammengeführt`);
    await dialog.getByRole('button', { name: 'Speichern', exact: true }).click();
    await expect(dialog.locator('h2')).toHaveText(`${title} zusammengeführt`);
    const stored = await (await page.request.get(path)).json();
    expect(stored.version).toBe(3);
    expect((await (await page.request.get(`${path}/history`)).json())).toHaveLength(3);
  } finally {
    testInfo.setTimeout(testInfo.timeout + 10_000);
    await page.request.post('/api/auth/login', { form: { username: 'admin@example.com', password } });
    expect((await page.request.delete(path)).status()).toBe(204);
  }
});
