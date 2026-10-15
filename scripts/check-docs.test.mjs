import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, realpathSync, rmSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { tmpdir } from 'node:os';
import test from 'node:test';
import { analyzeMarkdown, checkDocumentation, resolveLocalLink } from './check-docs.mjs';
import { fileURLToPath } from 'node:url';

function withFixture(files, run) {
  const parent = realpathSync(tmpdir());
  const directory = mkdtempSync(join(parent, 'smartdesk-docs-'));
  try {
    for (const [name, content] of Object.entries(files)) {
      const path = join(directory, name);
      mkdirSync(dirname(path), { recursive: true });
      writeFileSync(path, content);
    }
    run(directory);
  } finally {
    // Only remove the unique fixture directory created directly below the temp root.
    assert.equal(dirname(directory), parent);
    rmSync(directory, { recursive: true, force: true });
  }
}

test('headings support inline formatting, Unicode, punctuation and duplicates', () => {
  const result = analyzeMarkdown('# Ein `Titel`\n\n## Ein Titel\n\n## Prüfen & verstehen\n');
  assert.deepEqual([...result.headingIds], ['ein-titel', 'ein-titel-1', 'prüfen--verstehen']);
});

test('fenced examples are not mistaken for real links', () => {
  const result = analyzeMarkdown('```text\n# Beispiel\n[Falsch](missing.md)\n```\n\n[Echt](real.md)\n');
  assert.deepEqual(result.links.map(link => link.url), ['real.md']);
  assert.equal(result.links[0].line, 6);
});

test('reference links, images and destinations with spaces are parsed', () => {
  const result = analyzeMarkdown('[Quelle][Code]\n\n![Bild](image.png)\n\n[Datei](<My File.md>)\n\n[code]: source.ts\n');
  assert.deepEqual(result.links.map(link => link.url), ['source.ts', 'image.png', 'My File.md']);
});

test('commented examples in the handbook languages pass', () => {
  const result = analyzeMarkdown('```typescript\n// Zustand lesen\nvalue();\n```\n\n```html\n<!-- Eingabe -->\n<input />\n```\n\n```mermaid\n%% Datenweg\nflowchart LR\n A --> B\n```\n');
  assert.deepEqual(result.codeIssues, []);
});

test('unlabelled or uncommented learning examples are reported', () => {
  const result = analyzeMarkdown('```\nvalue();\n```\n\n```typescript\nvalue();\n```\n');
  assert.equal(result.codeIssues.length, 2);
  assert.match(result.codeIssues[0].message, /Sprachangabe/);
  assert.match(result.codeIssues[1].message, /Kommentar/);
});

test('JSONC and PowerShell comments are accepted', () => {
  assert.deepEqual(analyzeMarkdown('```jsonc\n{\n // Version\n "version": 1\n}\n```\n\n```powershell\n# Testlauf\nnpm test\n```').codeIssues, []);
});

test('external links are not treated as filesystem paths', () => {
  const root = resolve('repository');
  const file = join(root, 'docs', 'guide.md');
  for (const url of ['https://example.com', 'mailto:a@example.com', '//example.com']) assert.equal(resolveLocalLink(root, file, url), null);
});

test('relative, encoded, root-relative and fragment-only destinations resolve', () => {
  const root = resolve('repository');
  const file = join(root, 'docs', 'guide.md');
  assert.deepEqual(resolveLocalLink(root, file, '../README.md#start'), { target: join(root, 'README.md'), fragment: 'start' });
  assert.deepEqual(resolveLocalLink(root, file, 'My%20File.md#%C3%BCbung'), { target: join(root, 'docs', 'My File.md'), fragment: 'übung' });
  assert.deepEqual(resolveLocalLink(root, file, '/README.md'), { target: join(root, 'README.md'), fragment: '' });
  assert.deepEqual(resolveLocalLink(root, file, '#hier'), { target: file, fragment: 'hier' });
});

test('links cannot escape the repository and invalid encoding is rejected', () => {
  const root = resolve('repository');
  const file = join(root, 'docs', 'guide.md');
  assert.throws(() => resolveLocalLink(root, file, '../../outside.md'), /ausserhalb/);
  assert.throws(() => resolveLocalLink(root, file, 'invalid%zz.md'), URIError);
});

test('the complete scan reports missing local files', () => {
  withFixture({ 'README.md': '# Start\n\n[Fehlt](docs/missing.md)', 'docs/guide.md': '# Guide' }, root => {
    const result = checkDocumentation(root);
    assert.equal(result.issues.length, 1);
    assert.match(result.issues[0], /README.md:3: docs\/missing.md: Lokales Ziel existiert nicht/);
  });
});

test('the complete scan reports missing headings in existing files', () => {
  withFixture({ 'README.md': '# Start\n\n[Fehlt](docs/guide.md#missing)', 'docs/guide.md': '# Guide' }, root => {
    const result = checkDocumentation(root);
    assert.equal(result.issues.length, 1);
    assert.match(result.issues[0], /Zielueberschrift existiert nicht/);
  });
});

test('the checked-in documentation passes the complete local scan', () => {
  const root = fileURLToPath(new URL('../', import.meta.url));
  assert.deepEqual(checkDocumentation(root).issues, []);
});

test('public docs never depend on private learning files, even if present locally', () => {
  withFixture({ 'README.md': '[Privat](notes/guide.md)', 'notes/guide.md': '# Lokal' }, root => {
    assert.match(checkDocumentation(root).issues[0], /privaten oder generierten Bereich/);
    assert.match(checkDocumentation(root, { includePrivate: true }).issues[0], /privaten oder generierten Bereich/);
  });
});

test('public docs reject generated outputs and secrets but permit the environment template', () => {
  for (const path of ['output/export.pdf', 'tmp/result.md', 'backups/data.sql', '.env', '.env.production', 'backend/.env', 'frontend/dist/index.html']) {
    withFixture({ 'README.md': `[Lokal](${path})`, [path]: 'Nur lokal' }, root => {
      assert.match(checkDocumentation(root).issues[0], /privaten oder generierten Bereich/);
    });
  }
  withFixture({ 'README.md': '[Vorlage](.env.example)', '.env.example': 'KEY=placeholder' }, root => {
    assert.deepEqual(checkDocumentation(root).issues, []);
  });
});

test('private handbook is opt-in and may refer to public sources and private PDF', () => {
  withFixture({
    'README.md': '# Projekt',
    'notes/handbuch/README.md': '# Lernen\n\n[Projekt](../../README.md)\n\n[PDF](../guide.pdf)',
    'notes/guide.pdf': 'Fixture, no PDF parsing needed',
  }, root => {
    assert.equal(checkDocumentation(root).files, 1);
    const result = checkDocumentation(root, { includePrivate: true });
    assert.equal(result.files, 2);
    assert.equal(result.localLinks, 2);
    assert.deepEqual(result.issues, []);
  });
});

test('private handbook comment standard is checked only in opt-in scan', () => {
  withFixture({ 'README.md': '# Projekt', 'notes/handbuch/chapter.md': '```typescript\nvalue();\n```' }, root => {
    assert.deepEqual(checkDocumentation(root).issues, []);
    assert.match(checkDocumentation(root, { includePrivate: true }).issues[0], /Kommentar/);
  });
});

test('frontend README is included in public link checks', () => {
  withFixture({ 'README.md': '# Projekt', 'frontend/README.md': '[Fehlt](missing.ts)' }, root => {
    const result = checkDocumentation(root);
    assert.equal(result.files, 2);
    assert.match(result.issues[0], /frontend\/README.md/);
  });
});
