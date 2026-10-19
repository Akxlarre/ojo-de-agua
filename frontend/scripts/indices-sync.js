#!/usr/bin/env node
/**
 * indices-sync.js — Auto-indexer (WI-8)
 *
 * Escanea el proyecto Angular usando el AST de TypeScript y actualiza
 * automáticamente las secciones entre marcadores en los archivos indices/*.md
 *
 * Marcadores soportados (en cada índice):
 *   <!-- AUTO-GENERATED:BEGIN -->
 *   <!-- AUTO-GENERATED:END -->
 *
 * Solo reescribe entre los marcadores, preservando el contenido manual del resto.
 *
 * Uso: npm run indices:sync
 */

import fs from 'fs';
import path from 'path';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);
const ts = require('typescript');

// ─── Colors ──────────────────────────────────────────────────────────────────
const green  = (s) => `\x1b[32m${s}\x1b[0m`;
const yellow = (s) => `\x1b[33m${s}\x1b[0m`;
const cyan   = (s) => `\x1b[36m${s}\x1b[0m`;
const bold   = (s) => `\x1b[1m${s}\x1b[0m`;
const dim    = (s) => `\x1b[2m${s}\x1b[0m`;

const ROOT        = process.cwd();
const INDICES_DIR = path.join(ROOT, 'indices');
const SRC_APP     = path.join(ROOT, 'src', 'app');
const CACHE_DIR   = path.join(ROOT, '.claude', 'temp');
const CACHE_FILE  = path.join(CACHE_DIR, 'indices-cache.json');

// ─── mtime Cache ────────────────────────────────────────────────────────────

function loadCache() {
  try {
    return JSON.parse(fs.readFileSync(CACHE_FILE, 'utf-8'));
  } catch {
    return {};
  }
}

function saveCache(cache) {
  fs.mkdirSync(CACHE_DIR, { recursive: true });
  fs.writeFileSync(CACHE_FILE, JSON.stringify(cache), 'utf-8');
}

/**
 * Reads a file only if it changed since last run (by mtime).
 * Returns { content, changed } or { content: null, changed: false } if cached.
 */
function readIfChanged(filePath, cache) {
  const mtimeMs = fs.statSync(filePath).mtimeMs;
  if (cache[filePath] && cache[filePath] >= mtimeMs) {
    return { content: null, changed: false };
  }
  cache[filePath] = mtimeMs;
  return { content: fs.readFileSync(filePath, 'utf-8'), changed: true };
}

// ─── AST Utilities ───────────────────────────────────────────────────────────

function walkAst(node, visitor) {
  visitor(node);
  ts.forEachChild(node, child => walkAst(child, visitor));
}

function extractInterfaces(sourceFile) {
  const names = [];
  walkAst(sourceFile, node => {
    if (ts.isInterfaceDeclaration(node)) names.push(node.name.text);
    if (ts.isTypeAliasDeclaration(node)) names.push(node.name.text);
  });
  return names;
}

function extractSelector(sourceFile) {
  let selector = null;
  walkAst(sourceFile, node => {
    if (!ts.isPropertyAssignment(node)) return;
    if (node.name?.getText(sourceFile) === 'selector') {
      selector = node.initializer?.getText(sourceFile)?.replace(/['"]/g, '') ?? null;
    }
  });
  return selector;
}

function extractSignalInputsOutputs(content) {
  const inputs  = [];
  const outputs = [];
  const inRe  = /(\w+)\s*=\s*input[^(]*\(/g;
  const outRe = /(\w+)\s*=\s*output[^(]*\(/g;
  let m;
  while ((m = inRe.exec(content))  !== null) inputs.push(m[1]);
  while ((m = outRe.exec(content)) !== null) outputs.push(m[1]);
  return { inputs, outputs };
}

function extractInjected(content) {
  const deps = [];
  const re = /inject\s*\(\s*(\w+)\s*\)/g;
  let m;
  while ((m = re.exec(content)) !== null) deps.push(m[1]);
  return [...new Set(deps)];
}

function extractPublicSignals(content) {
  const signals = [];
  const re = /public\s+readonly\s+(\w+)\s*=/g;
  let m;
  while ((m = re.exec(content)) !== null) signals.push(m[1]);
  return signals;
}

/**
 * Extracts inline template content from a component .ts file.
 * Falls back to reading external templateUrl if no inline template found.
 */
function extractTemplateContent(tsContent, filePath) {
  // Try inline template: template: `...`
  const inlineMatch = tsContent.match(/template\s*:\s*`([\s\S]*?)`/);
  if (inlineMatch) return inlineMatch[1];

  // Fallback: external templateUrl
  const urlMatch = tsContent.match(/templateUrl\s*:\s*['"](.+?)['"]/);
  if (urlMatch) {
    const htmlPath = path.resolve(path.dirname(filePath), urlMatch[1]);
    if (fs.existsSync(htmlPath)) return fs.readFileSync(htmlPath, 'utf-8');
  }

  return '';
}

/**
 * Detects UI patterns in a template string.
 * Returns { loading, empty, error, skeleton } booleans.
 */
function detectPagePatterns(templateContent) {
  const t = templateContent;
  return {
    loading:  /isLoading\s*\(/.test(t) || /\bloading\]/.test(t),
    empty:    /app-empty-state/.test(t) || /emptymessage/.test(t),
    error:    /app-alert-card[\s\S]{0,120}error/.test(t) || /error-state/.test(t) || /\.error\s*\(/.test(t),
    skeleton: /skeleton-block/.test(t) || /-skeleton[\s>"']/.test(t),
  };
}

// ─── Directory Walker ─────────────────────────────────────────────────────────

function* walkDir(dir) {
  if (!fs.existsSync(dir)) return;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) yield* walkDir(fullPath);
    else yield fullPath;
  }
}

// ─── Data Collection ──────────────────────────────────────────────────────────

function collectComponents(cache, prevResults) {
  const results = [];
  const prevMap = new Map((prevResults ?? []).map(r => [r.filePath, r]));
  let skipped = 0;
  const sharedDir = path.join(SRC_APP, 'shared');
  for (const filePath of walkDir(sharedDir)) {
    if (!filePath.endsWith('.component.ts') || filePath.endsWith('.spec.ts')) continue;
    if (filePath.endsWith('-skeleton.component.ts')) continue;
    const relPath = path.relative(ROOT, filePath).replace(/\\/g, '/');
    try {
      const { content, changed } = readIfChanged(filePath, cache);
      if (!changed && prevMap.has(relPath)) { results.push(prevMap.get(relPath)); skipped++; continue; }
      const src = content ?? fs.readFileSync(filePath, 'utf-8');
      const sf = ts.createSourceFile(filePath, src, ts.ScriptTarget.Latest, true);
      const selector = extractSelector(sf);
      const { inputs, outputs } = extractSignalInputsOutputs(src);
      results.push({ selector: selector ?? path.basename(filePath, '.component.ts'), inputs, outputs, filePath: relPath });
    } catch { /* skip unparseable */ }
  }
  if (skipped > 0) process.stdout.write(dim(` (${skipped} cached)`));
  return results;
}

function collectServices(cache, prevResults) {
  const results = [];
  const prevMap = new Map((prevResults ?? []).map(r => [r.filePath, r]));
  let skipped = 0;
  const coreDir = path.join(SRC_APP, 'core');
  for (const filePath of walkDir(coreDir)) {
    if (!filePath.endsWith('.service.ts') || filePath.endsWith('.spec.ts')) continue;
    if (filePath.endsWith('.facade.ts')) continue;
    const relPath = path.relative(ROOT, filePath).replace(/\\/g, '/');
    try {
      const { content, changed } = readIfChanged(filePath, cache);
      if (!changed && prevMap.has(relPath)) { results.push(prevMap.get(relPath)); skipped++; continue; }
      const src = content ?? fs.readFileSync(filePath, 'utf-8');
      const classMatch = src.match(/export\s+class\s+(\w+)/);
      const className = classMatch?.[1] ?? path.basename(filePath, '.ts');
      results.push({ className, deps: extractInjected(src), filePath: relPath });
    } catch { /* skip */ }
  }
  if (skipped > 0) process.stdout.write(dim(` (${skipped} cached)`));
  return results;
}

function collectFacades(cache, prevResults) {
  const results = [];
  const prevMap = new Map((prevResults ?? []).map(r => [r.filePath, r]));
  let skipped = 0;
  const coreDir = path.join(SRC_APP, 'core');
  for (const filePath of walkDir(coreDir)) {
    if (!filePath.endsWith('.facade.ts') || filePath.endsWith('.spec.ts')) continue;
    const relPath = path.relative(ROOT, filePath).replace(/\\/g, '/');
    try {
      const { content, changed } = readIfChanged(filePath, cache);
      if (!changed && prevMap.has(relPath)) { results.push(prevMap.get(relPath)); skipped++; continue; }
      const src = content ?? fs.readFileSync(filePath, 'utf-8');
      const classMatch = src.match(/export\s+class\s+(\w+)/);
      const className = classMatch?.[1] ?? path.basename(filePath, '.ts');
      results.push({ className, deps: extractInjected(src), signals: extractPublicSignals(src), filePath: relPath });
    } catch { /* skip */ }
  }
  if (skipped > 0) process.stdout.write(dim(` (${skipped} cached)`));
  return results;
}

function collectModels(cache, prevResults) {
  const results = [];
  const prevMap = new Map((prevResults ?? []).map(r => [r.filePath, r]));
  let skipped = 0;
  const modelsDir = path.join(SRC_APP, 'core', 'models');
  for (const filePath of walkDir(modelsDir)) {
    if (!filePath.endsWith('.model.ts') || filePath.endsWith('.spec.ts')) continue;
    const relPath = path.relative(ROOT, filePath).replace(/\\/g, '/');
    try {
      const { content, changed } = readIfChanged(filePath, cache);
      if (!changed && prevMap.has(relPath)) { results.push(prevMap.get(relPath)); skipped++; continue; }
      const src = content ?? fs.readFileSync(filePath, 'utf-8');
      const sf = ts.createSourceFile(filePath, src, ts.ScriptTarget.Latest, true);
      const interfaces = extractInterfaces(sf);
      if (interfaces.length === 0) continue;
      const category = relPath.includes('/dto/') ? 'dto' : relPath.includes('/ui/') ? 'ui' : 'other';
      results.push({ interfaces, filePath: relPath, category });
    } catch { /* skip */ }
  }
  if (skipped > 0) process.stdout.write(dim(` (${skipped} cached)`));
  return results;
}

function collectUsageMap(cache, prevResults, sharedSelectors) {
  const results = { componentUsage: {}, facadeUsage: {}, serviceUsage: {}, pagePatterns: [] };
  const prevPages = new Map((prevResults?.pagePatterns ?? []).map(r => [r.filePath, r]));
  let skipped = 0;

  // Build set of known shared selectors from COMPONENTS scan
  const selectors = new Set(sharedSelectors);

  // Scan features/ and layout/
  const scanDirs = [
    { dir: path.join(SRC_APP, 'features'), isPage: true },
    { dir: path.join(SRC_APP, 'layout'),   isPage: false },
  ];

  for (const { dir, isPage } of scanDirs) {
    for (const filePath of walkDir(dir)) {
      if (!filePath.endsWith('.component.ts') || filePath.endsWith('.spec.ts')) continue;
      const relPath = path.relative(ROOT, filePath).replace(/\\/g, '/');
      // Consumer label: e.g. "features/dashboard" or "layout/sidebar"
      const consumer = relPath
        .replace(/^src\/app\//, '')
        .replace(/\/[^/]+\.component\.ts$/, '');

      try {
        const { content, changed } = readIfChanged(filePath, cache);
        const src = content ?? fs.readFileSync(filePath, 'utf-8');

        // If unchanged and we have prev data, reuse it
        if (!changed && prevPages.has(relPath)) {
          const prev = prevPages.get(relPath);
          // Restore usage maps from prev
          if (prev._componentHits) prev._componentHits.forEach(s => {
            (results.componentUsage[s] ??= new Set()).add(consumer);
          });
          if (prev._facadeHits) prev._facadeHits.forEach(f => {
            (results.facadeUsage[f] ??= new Set()).add(consumer);
          });
          if (prev._serviceHits) prev._serviceHits.forEach(s => {
            (results.serviceUsage[s] ??= new Set()).add(consumer);
          });
          if (isPage) results.pagePatterns.push(prev);
          skipped++;
          continue;
        }

        // Extract template (inline primary, external fallback)
        const templateContent = extractTemplateContent(src, filePath);

        // Detect shared component usage in template
        const componentHits = [];
        for (const sel of selectors) {
          const tagRe = new RegExp(`<${sel}[\\s/>]`);
          if (tagRe.test(templateContent)) {
            (results.componentUsage[sel] ??= new Set()).add(consumer);
            componentHits.push(sel);
          }
        }

        // Detect injected facades and services
        const injected = extractInjected(src);
        const facadeHits = [];
        const serviceHits = [];
        for (const dep of injected) {
          if (dep.endsWith('Facade')) {
            (results.facadeUsage[dep] ??= new Set()).add(consumer);
            facadeHits.push(dep);
          } else if (dep.endsWith('Service')) {
            (results.serviceUsage[dep] ??= new Set()).add(consumer);
            serviceHits.push(dep);
          }
        }

        // Page patterns (only for features/, not layout/)
        if (isPage) {
          const patterns = detectPagePatterns(templateContent);
          results.pagePatterns.push({
            page: consumer,
            filePath: relPath,
            patterns,
            _componentHits: componentHits,
            _facadeHits: facadeHits,
            _serviceHits: serviceHits,
          });
        }
      } catch { /* skip unparseable */ }
    }
  }

  // Convert Sets to sorted arrays for serialization
  for (const key of Object.keys(results.componentUsage)) {
    results.componentUsage[key] = [...results.componentUsage[key]].sort();
  }
  for (const key of Object.keys(results.facadeUsage)) {
    results.facadeUsage[key] = [...results.facadeUsage[key]].sort();
  }
  for (const key of Object.keys(results.serviceUsage)) {
    results.serviceUsage[key] = [...results.serviceUsage[key]].sort();
  }

  if (skipped > 0) process.stdout.write(dim(` (${skipped} cached)`));
  return results;
}

// ─── Markdown Table Generators ────────────────────────────────────────────────

function generateComponentsTable(items) {
  if (items.length === 0) return '_Sin componentes auto-detectados aún._\n';
  const header = '| Selector | Inputs | Outputs | Archivo |\n|----------|--------|---------|---------|';
  const rows = items.map(c => {
    const ins  = c.inputs.length  > 0 ? c.inputs.map(i => `\`${i}\``).join(', ') : '—';
    const outs = c.outputs.length > 0 ? c.outputs.map(o => `\`${o}\``).join(', ') : '—';
    return `| \`${c.selector}\` | ${ins} | ${outs} | \`${c.filePath}\` |`;
  });
  return header + '\n' + rows.join('\n') + '\n';
}

function generateServicesTable(items) {
  if (items.length === 0) return '_Sin servicios auto-detectados aún._\n';
  const header = '| Clase | Dependencias | Archivo |\n|-------|-------------|---------|';
  const rows = items.map(s => {
    const deps = s.deps.length > 0 ? s.deps.map(d => `\`${d}\``).join(', ') : '—';
    return `| \`${s.className}\` | ${deps} | \`${s.filePath}\` |`;
  });
  return header + '\n' + rows.join('\n') + '\n';
}

function generateFacadesTable(items) {
  if (items.length === 0) return '_Sin facades auto-detectadas aún._\n';
  const header = '| Clase | Dependencias | Signals expuestos | Archivo |\n|-------|-------------|------------------|---------|';
  const rows = items.map(f => {
    const deps = f.deps.length    > 0 ? f.deps.map(d => `\`${d}\``).join(', ') : '—';
    const sigs = f.signals.length > 0 ? f.signals.map(s => `\`${s}\``).join(', ') : '—';
    return `| \`${f.className}\` | ${deps} | ${sigs} | \`${f.filePath}\` |`;
  });
  return header + '\n' + rows.join('\n') + '\n';
}

function generateModelsTable(items) {
  if (items.length === 0) return '_Sin modelos auto-detectados aún._\n';
  const header = '| Interfaces | Categoría | Archivo |\n|-----------|----------|---------|';
  const rows = items.map(m => {
    const ifaces = m.interfaces.map(i => `\`${i}\``).join(', ');
    return `| ${ifaces} | \`${m.category}\` | \`${m.filePath}\` |`;
  });
  return header + '\n' + rows.join('\n') + '\n';
}

function generateUsageMapContent(usageData) {
  const lines = [];

  // ── Componentes shared → Consumidores
  const compEntries = Object.entries(usageData.componentUsage).sort((a, b) => a[0].localeCompare(b[0]));
  if (compEntries.length > 0) {
    lines.push('## Componentes shared → Consumidores\n');
    lines.push('| Componente | Usado en |');
    lines.push('|------------|----------|');
    for (const [sel, consumers] of compEntries) {
      lines.push(`| \`${sel}\` | ${consumers.map(c => `\`${c}\``).join(', ')} |`);
    }
    lines.push('');
  }

  // ── Facades → Consumidores
  const facEntries = Object.entries(usageData.facadeUsage).sort((a, b) => a[0].localeCompare(b[0]));
  if (facEntries.length > 0) {
    lines.push('## Facades → Consumidores\n');
    lines.push('| Facade | Inyectada en |');
    lines.push('|--------|-------------|');
    for (const [name, consumers] of facEntries) {
      lines.push(`| \`${name}\` | ${consumers.map(c => `\`${c}\``).join(', ')} |`);
    }
    lines.push('');
  }

  // ── Services → Consumidores
  const svcEntries = Object.entries(usageData.serviceUsage).sort((a, b) => a[0].localeCompare(b[0]));
  if (svcEntries.length > 0) {
    lines.push('## Services → Consumidores\n');
    lines.push('| Service | Inyectado en |');
    lines.push('|---------|-------------|');
    for (const [name, consumers] of svcEntries) {
      lines.push(`| \`${name}\` | ${consumers.map(c => `\`${c}\``).join(', ')} |`);
    }
    lines.push('');
  }

  // ── Matriz de patrones por página (solo features/, no layout/)
  if (usageData.pagePatterns.length > 0) {
    lines.push('## Matriz de patrones por página\n');
    lines.push('| Página | Loading | Empty | Error | Skeleton |');
    lines.push('|--------|---------|-------|-------|----------|');
    const sorted = [...usageData.pagePatterns].sort((a, b) => a.page.localeCompare(b.page));
    for (const entry of sorted) {
      const p = entry.patterns;
      const flag = (v) => v ? '✅' : '❌';
      lines.push(`| \`${entry.page}\` | ${flag(p.loading)} | ${flag(p.empty)} | ${flag(p.error)} | ${flag(p.skeleton)} |`);
    }
    lines.push('');
  }

  return lines.length > 0 ? lines.join('\n') + '\n' : '_Sin consumidores detectados aún._\n';
}

// ─── Marker Injection ─────────────────────────────────────────────────────────

const MARKER_BEGIN = '<!-- AUTO-GENERATED:BEGIN -->';
const MARKER_END   = '<!-- AUTO-GENERATED:END -->';

function injectGenerated(filePath, generatedContent) {
  if (!fs.existsSync(filePath)) {
    console.warn(yellow(`  ⚠  No existe: ${path.relative(ROOT, filePath)}`));
    return false;
  }

  const original = fs.readFileSync(filePath, 'utf-8');
  const beginIdx = original.indexOf(MARKER_BEGIN);
  const endIdx   = original.indexOf(MARKER_END);

  if (beginIdx === -1 || endIdx === -1) {
    console.warn(yellow(`  ⚠  Sin marcadores en ${path.basename(filePath)} — agrega los marcadores AUTO-GENERATED`));
    return false;
  }

  const before     = original.slice(0, beginIdx + MARKER_BEGIN.length);
  const after      = original.slice(endIdx);
  const newContent = `${before}\n${generatedContent}\n${after}`;

  if (newContent === original) return false;
  fs.writeFileSync(filePath, newContent, 'utf-8');
  return true;
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  console.log(bold(cyan('🔄  indices:sync — Auto-indexer (AST Mode + Incremental Cache)\n')));

  if (!fs.existsSync(INDICES_DIR)) {
    console.error(`\x1b[31mNo se encontró el directorio indices/ en ${ROOT}\x1b[0m`);
    process.exit(1);
  }

  // Load mtime cache and previous results from last run
  const cacheData = loadCache();
  const cache = cacheData.mtimes ?? {};
  const prev  = cacheData.results ?? {};

  // Invalidate cache if this script itself changed
  const selfPath = new URL(import.meta.url).pathname.replace(/^\/([A-Z]:)/, '$1');
  const selfMtime = fs.statSync(selfPath).mtimeMs;
  if (cacheData.scriptMtime && cacheData.scriptMtime !== selfMtime) {
    console.log(dim('  Cache invalidado (script modificado)\n'));
    Object.keys(cache).forEach(k => delete cache[k]);
  }

  const changes = [];

  // ── COMPONENTS.md ──────────────────────────────────────────────────────────
  process.stdout.write(dim('  Escaneando shared/components/**/*.component.ts...'));
  const components  = collectComponents(cache, prev.components);
  const compChanged = injectGenerated(
    path.join(INDICES_DIR, 'COMPONENTS.md'),
    generateComponentsTable(components),
  );
  process.stdout.write('\r');
  console.log(compChanged
    ? green(`  ✓ COMPONENTS.md actualizado (${components.length} componentes detectados)`)
    : dim(`  — COMPONENTS.md sin cambios    (${components.length} componentes detectados)`),
  );
  if (compChanged) changes.push('COMPONENTS.md');

  // ── SERVICES.md ────────────────────────────────────────────────────────────
  process.stdout.write(dim('  Escaneando core/services/**/*.service.ts...'));
  const services  = collectServices(cache, prev.services);
  const svcChanged = injectGenerated(
    path.join(INDICES_DIR, 'SERVICES.md'),
    generateServicesTable(services),
  );
  process.stdout.write('\r');
  console.log(svcChanged
    ? green(`  ✓ SERVICES.md actualizado (${services.length} servicios detectados)`)
    : dim(`  — SERVICES.md sin cambios    (${services.length} servicios detectados)`),
  );
  if (svcChanged) changes.push('SERVICES.md');

  // ── FACADES.md ─────────────────────────────────────────────────────────────
  process.stdout.write(dim('  Escaneando core/**/*.facade.ts...'));
  const facades  = collectFacades(cache, prev.facades);
  const facChanged = injectGenerated(
    path.join(INDICES_DIR, 'FACADES.md'),
    generateFacadesTable(facades),
  );
  process.stdout.write('\r');
  console.log(facChanged
    ? green(`  ✓ FACADES.md actualizado (${facades.length} facades detectadas)`)
    : dim(`  — FACADES.md sin cambios    (${facades.length} facades detectadas)`),
  );
  if (facChanged) changes.push('FACADES.md');

  // ── MODELS.md ──────────────────────────────────────────────────────────────
  process.stdout.write(dim('  Escaneando core/models/**/*.model.ts...'));
  const models  = collectModels(cache, prev.models);
  const modChanged = injectGenerated(
    path.join(INDICES_DIR, 'MODELS.md'),
    generateModelsTable(models),
  );
  process.stdout.write('\r');
  console.log(modChanged
    ? green(`  ✓ MODELS.md actualizado (${models.length} modelos detectados)`)
    : dim(`  — MODELS.md sin cambios    (${models.length} modelos detectados)`),
  );
  if (modChanged) changes.push('MODELS.md');

  // ── USAGE-MAP.md ───────────────────────────────────────────────────────────
  process.stdout.write(dim('  Escaneando features/ y layout/ (usage map)...'));
  // Build selector list from previously collected components
  const sharedSelectors = components.map(c => c.selector).filter(Boolean);
  const usageMap  = collectUsageMap(cache, prev.usageMap, sharedSelectors);
  const usageChanged = injectGenerated(
    path.join(INDICES_DIR, 'USAGE-MAP.md'),
    generateUsageMapContent(usageMap),
  );
  process.stdout.write('\r');
  const pageCount = usageMap.pagePatterns.length;
  const compCount = Object.keys(usageMap.componentUsage).length;
  console.log(usageChanged
    ? green(`  ✓ USAGE-MAP.md actualizado (${pageCount} páginas, ${compCount} componentes mapeados)`)
    : dim(`  — USAGE-MAP.md sin cambios    (${pageCount} páginas, ${compCount} componentes mapeados)`),
  );
  if (usageChanged) changes.push('USAGE-MAP.md');

  // Persist cache for next run
  saveCache({
    scriptMtime: selfMtime,
    mtimes: cache,
    results: { components, services, facades, models, usageMap },
  });

  console.log('');
  if (changes.length > 0) {
    console.log(green(`✅  ${changes.length} índice(s) actualizado(s): ${changes.join(', ')}`));
  } else {
    console.log(green('✅  Todos los índices están al día. Sin cambios.'));
  }
}

main().catch(err => {
  console.error(`\x1b[31m${String(err?.message || err)}\x1b[0m`);
  process.exit(1);
});
