import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, extname, isAbsolute, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(new URL('../frontend/package.json', import.meta.url));
const { parsers } = require('prettier/plugins/markdown');

function* walk(node) {
  yield node;
  for (const child of node.children ?? []) yield* walk(child);
}

function nodeText(node) {
  if (node.value !== undefined) return node.value;
  if (node.alt !== undefined) return node.alt;
  return (node.children ?? []).map(nodeText).join('');
}

function hasComment(language, value) {
  if (['typescript', 'ts', 'javascript', 'js', 'jsonc'].includes(language)) return /^\s*(\/\/|\/\*)/m.test(value);
  if (['python', 'py', 'powershell', 'ps1', 'bash', 'sh', 'shell', 'yaml', 'yml', 'text'].includes(language)) return /^\s*#/m.test(value);
  if (['html', 'xml'].includes(language)) return value.includes('<!--');
  if (['css', 'scss'].includes(language)) return value.includes('/*');
  if (language === 'sql') return /^\s*--/m.test(value);
  if (language === 'mermaid') return /^\s*%%/m.test(value);
  return false;
}

export function analyzeMarkdown(content) {
  const nodes = [...walk(parsers.markdown.parse(content))];
  const definitions = new Map(nodes.filter(node => node.type === 'definition').map(node => [node.identifier.toLowerCase(), node.url]));
  const headingIds = new Set();
  const links = [];
  const codeIssues = [];

  for (const node of nodes) {
    if (node.type === 'heading') {
      // Matches the repository's Markdown headings, including Unicode and duplicate IDs.
      const base = nodeText(node).toLowerCase().replace(/[^\p{L}\p{N}\p{M}_\-\s]/gu, '').replace(/\s/g, '-');
      let id = base;
      let suffix = 0;
      while (headingIds.has(id)) id = `${base}-${++suffix}`;
      headingIds.add(id);
    }
    if (node.type === 'link' || node.type === 'image') links.push({ url: node.url, line: node.position.start.line });
    if (node.type === 'linkReference' || node.type === 'imageReference') {
      const url = definitions.get(node.identifier.toLowerCase());
      if (url) links.push({ url, line: node.position.start.line });
    }
    if (node.type === 'code') {
      const language = (node.lang ?? '').split(/\s/, 1)[0].toLowerCase();
      if (!language) codeIssues.push({ line: node.position.start.line, message: 'Lerncodeblock ohne Sprachangabe.' });
      else if (!hasComment(language, node.value)) codeIssues.push({ line: node.position.start.line, message: `Lerncodeblock (${language}) ohne erkennbaren Kommentar.` });
    }
  }
  return { headingIds, links, codeIssues };
}

export function resolveLocalLink(root, document, url) {
  if (/^([a-z][a-z\d+.-]*:|\/\/)/i.test(url)) return null;
  const hash = url.indexOf('#');
  const path = decodeURIComponent((hash < 0 ? url : url.slice(0, hash)).split('?', 1)[0]);
  const fragment = hash < 0 ? '' : decodeURIComponent(url.slice(hash + 1));
  const target = path ? resolve(path.startsWith('/') ? root : dirname(document), path.startsWith('/') ? path.slice(1) : path) : document;
  const fromRoot = relative(root, target);
  if (fromRoot === '..' || fromRoot.startsWith(`..${sep}`) || isAbsolute(fromRoot)) throw new Error('Verweis liegt ausserhalb des Repositorys.');
  return { target, fragment };
}

function markdownFiles(directory) {
  if (!existsSync(directory)) return [];
  return readdirSync(directory, { withFileTypes: true }).flatMap(entry => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return markdownFiles(path);
    return entry.isFile() && extname(path).toLowerCase() === '.md' ? [path] : [];
  });
}

function isPrivateTarget(root, target) {
  const path = relative(root, target).split(sep).join('/');
  return /^(notes|output|tmp|backups|\.git|\.vscode|\.agents|\.codex)(\/|$)/.test(path)
    || /(^|\/)(node_modules|dist|coverage|test-results|playwright-report|__pycache__|\.venv|\.angular|\.ruff_cache|\.pytest_cache)(\/|$)/.test(path)
    || /(^|\/)\.env($|\.(?!example$))/.test(path);
}

export function checkDocumentation(root, { includePrivate = false } = {}) {
  const files = [join(root, 'README.md'), ...markdownFiles(join(root, 'docs'))];
  const frontendReadme = join(root, 'frontend', 'README.md');
  if (existsSync(frontendReadme)) files.push(frontendReadme);
  if (includePrivate) {
    const overview = join(root, 'notes', 'README.md');
    if (existsSync(overview)) files.push(overview);
    files.push(...markdownFiles(join(root, 'notes', 'handbuch')));
  }
  files.sort();
  const cache = new Map();
  const read = path => {
    if (!cache.has(path)) cache.set(path, analyzeMarkdown(readFileSync(path, 'utf8')));
    return cache.get(path);
  };
  const issues = [];
  let localLinks = 0;

  for (const file of files) {
    const name = relative(root, file).split(sep).join('/');
    const analysis = read(file);
    const privateSource = name.startsWith('notes/');
    if (name.startsWith('notes/handbuch/')) {
      for (const issue of analysis.codeIssues) issues.push(`${name}:${issue.line}: ${issue.message}`);
    }
    for (const link of analysis.links) {
      try {
        const destination = resolveLocalLink(root, file, link.url);
        if (!destination) continue;
        localLinks++;
        if (!privateSource && isPrivateTarget(root, destination.target)) throw new Error('Oeffentlicher Verweis zeigt auf einen privaten oder generierten Bereich.');
        if (!existsSync(destination.target)) throw new Error('Lokales Ziel existiert nicht.');
        if (destination.fragment && statSync(destination.target).isFile() && extname(destination.target).toLowerCase() === '.md') {
          if (!read(destination.target).headingIds.has(destination.fragment)) throw new Error('Zielueberschrift existiert nicht.');
        }
      } catch (error) {
        issues.push(`${name}:${link.line}: ${link.url}: ${error.message}`);
      }
    }
  }
  return { files: files.length, localLinks, issues };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const root = fileURLToPath(new URL('../', import.meta.url));
  const args = process.argv.slice(2);
  if (args.some(arg => arg !== '--include-private')) throw new Error('Erlaubte Option: --include-private');
  const result = checkDocumentation(root, { includePrivate: args.includes('--include-private') });
  if (result.issues.length) {
    console.error(result.issues.join('\n'));
    process.exitCode = 1;
  } else {
    console.log(`${result.files} Markdown-Dateien und ${result.localLinks} lokale Verweise geprueft. Keine Fehler.`);
  }
}
