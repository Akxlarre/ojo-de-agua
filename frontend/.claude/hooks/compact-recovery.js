#!/usr/bin/env node
/**
 * compact-recovery.js — PostCompact Hook
 *
 * Se ejecuta automáticamente después de cada compactación de contexto.
 * Re-inyecta los índices del proyecto al contexto de Claude.
 *
 * Mejoras v2:
 *   - Inyección SELECTIVA: solo los índices que el agente ya había leído
 *     (más los 3 core siempre). Lee el discovery flag para decidir.
 *   - Inyección PARCIAL: corta en <!-- DETAIL:BEGIN --> para inyectar
 *     solo las tablas de Quick Reference, no los ejemplos de código.
 *
 * stdout → se agrega directamente al contexto de Claude.
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const cwd = process.cwd();
const sessionId = process.env.CLAUDE_SESSION_ID || 'default';
const DETAIL_MARKER = '<!-- DETAIL:BEGIN -->';

// Índices siempre inyectados (base de todo proyecto)
const CORE_INDICES = new Set(['COMPONENTS', 'SERVICES', 'FACADES', 'USAGE-MAP']);

// Mapa completo de índices disponibles
const ALL_INDEX_FILES = {
  COMPONENTS: 'indices/COMPONENTS.md',
  SERVICES: 'indices/SERVICES.md',
  FACADES: 'indices/FACADES.md',
  'USAGE-MAP': 'indices/USAGE-MAP.md',
  MODELS: 'indices/MODELS.md',
  DATABASE: 'indices/DATABASE.md',
  DIRECTIVES: 'indices/DIRECTIVES.md',
  STYLES: 'indices/STYLES.md',
  PIPES: 'indices/PIPES.md',
  'ANTI-PATTERNS': 'indices/ANTI-PATTERNS.md',
  STORES: 'indices/STORES.md',
};

// ─── Leer discovery flag: qué índices leyó el agente antes del compact ───────
const touchedIndexNames = new Set(CORE_INDICES);
try {
  const flagPath = path.join(os.tmpdir(), `koa-discovery-${sessionId}.flag`);
  if (fs.existsSync(flagPath)) {
    const flagContent = fs.readFileSync(flagPath, 'utf-8');
    for (const line of flagContent.split('\n')) {
      const match = line.match(/indices\/([\w-]+)\.md/i);
      if (match) touchedIndexNames.add(match[1].toUpperCase());
    }
  }
} catch { /* fail-open — solo CORE */ }

// ─── Construir output ────────────────────────────────────────────────────────
let output = '';
output += '[POST-COMPACT] Índices restaurados (Quick Reference):\n\n';

let injectedCount = 0;

for (const [name, relativePath] of Object.entries(ALL_INDEX_FILES)) {
  if (!touchedIndexNames.has(name)) continue;

  const fullPath = path.join(cwd, relativePath);
  if (!fs.existsSync(fullPath)) continue;

  let content = fs.readFileSync(fullPath, 'utf-8').trim();
  if (!content) continue;

  // Cortar en DETAIL:BEGIN — inyectar solo la Quick Reference
  const cutoff = content.indexOf(DETAIL_MARKER);
  if (cutoff > -1) content = content.slice(0, cutoff).trim();

  output += `--- ${relativePath} ---\n`;
  output += content + '\n\n';
  injectedCount++;
}

if (injectedCount === 0) {
  output += '(Sin índices encontrados)\n';
} else {
  output += `[${injectedCount} índices — para detalles: lee el archivo directamente]\n`;
}

// ─── Context files (domain + brief) ──────────────────────────────────────────
// Inyectar contexto semántico privado si existe y tiene contenido útil
const CONTEXT_FILES = [
  { label: 'context/domain.md',      path: 'context/domain.md'      },
  { label: 'context/brief.md',       path: 'context/brief.md'       },
  { label: 'context/constraints.md', path: 'context/constraints.md' },
  { label: 'context/learnings.md',   path: 'context/learnings.md'   },
];

let contextAdded = false;
for (const cf of CONTEXT_FILES) {
  const fullPath = path.join(cwd, cf.path);
  if (!fs.existsSync(fullPath)) continue;

  const raw = fs.readFileSync(fullPath, 'utf-8').trim();
  // Saltar archivos que son solo plantilla (sin contenido real)
  const stripped = raw.replace(/<!--[\s\S]*?-->/g, '').trim();
  if (stripped.length < 80) continue;

  if (!contextAdded) {
    output += '\n[CONTEXT]\n';
    contextAdded = true;
  }
  output += '--- ' + cf.label + ' ---\n';
  output += raw + '\n\n';
}

process.stdout.write(output);
