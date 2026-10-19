#!/usr/bin/env node
/**
 * spec-diff-check.js — PreToolUse Hook (Bash — detecta git commit)
 *
 * Verifica que los nuevos componentes y facades creados en la sesión
 * estén registrados en sus índices correspondientes ANTES de commitear.
 *
 * Flujo:
 *   1. Lee session-writes.json (archivos fuente modificados esta sesión)
 *   2. Para cada componente nuevo (shared/components/*.component.ts) → verifica COMPONENTS.md
 *   3. Para cada facade nueva (core/services/*.facade.ts) → verifica FACADES.md
 *   4. Si falta alguno → exit 2 con instrucción clara
 *
 * Exit codes:
 *   0 = permitir el commit
 *   2 = bloquear el commit con mensaje de qué falta actualizar
 */

const fs = require('fs');
const path = require('path');

// Solo aplica a comandos git commit
const toolInput = process.env.TOOL_INPUT || '{}';
let cmd = '';
try { cmd = JSON.parse(toolInput).command || ''; } catch { /* ignore */ }

if (!cmd.includes('git') || !cmd.includes('commit')) {
  process.exit(0);
}

const sessionWritesPath = path.join(process.cwd(), '.claude', 'temp', 'session-writes.json');
if (!fs.existsSync(sessionWritesPath)) process.exit(0);

let sessionWrites = [];
try {
  sessionWrites = JSON.parse(fs.readFileSync(sessionWritesPath, 'utf8'));
} catch { process.exit(0); }

if (!Array.isArray(sessionWrites) || sessionWrites.length === 0) process.exit(0);

const missing = [];

// ─── Leer índices ──────────────────────────────────────────────────────────
function readIndex(relPath) {
  const fullPath = path.join(process.cwd(), relPath);
  if (!fs.existsSync(fullPath)) return '';
  return fs.readFileSync(fullPath, 'utf8');
}

const componentsIndex = readIndex('indices/COMPONENTS.md');
const facadesIndex    = readIndex('indices/FACADES.md');
const servicesIndex   = readIndex('indices/SERVICES.md');

// ─── Verificar componentes nuevos ────────────────────────────────────────
const componentRe = /shared\/components\/([^\/]+)\/\1\.component\.ts$/;
for (const writtenPath of sessionWrites) {
  const norm = writtenPath.replace(/\\/g, '/');
  const match = norm.match(/shared\/components\/([^/]+)\/[^/]+\.component\.ts$/);
  if (!match) continue;

  const componentName = match[1]; // e.g. "kpi-card"
  const selectorName = `app-${componentName}`;

  if (!componentsIndex.includes(selectorName) && !componentsIndex.includes(componentName)) {
    missing.push(`  - <${selectorName}> no está en indices/COMPONENTS.md`);
  }
}

// ─── Verificar facades nuevas ────────────────────────────────────────────
for (const writtenPath of sessionWrites) {
  const norm = writtenPath.replace(/\\/g, '/');
  if (!norm.includes('core/services/') || !norm.endsWith('.facade.ts')) continue;

  const fileName = path.basename(norm, '.facade.ts'); // e.g. "auth"
  const facadeName = fileName.split('-').map(w => w[0].toUpperCase() + w.slice(1)).join('') + 'Facade';

  if (!facadesIndex.includes(facadeName) && !servicesIndex.includes(facadeName)) {
    missing.push(`  - ${facadeName} no está en indices/FACADES.md`);
  }
}

// ─── Reportar ──────────────────────────────────────────────────────────
if (missing.length > 0) {
  process.stderr.write(
    '\u{1F4CB} SPEC-DIFF-CHECK: Tienes artefactos sin registrar en los índices:\n' +
    missing.join('\n') +
    '\n\nActualiza los índices antes de commitear:\n' +
    '  - npm run indices:sync (auto-detecta via AST)\n' +
    '  - O edita manualmente los .md en indices/\n' +
    '  - Luego vuelve a ejecutar git commit'
  );
  process.exit(2);
}

process.exit(0);
