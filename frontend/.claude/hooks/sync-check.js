#!/usr/bin/env node
/**
 * sync-check.js — Stop Hook (command)
 *
 * Reemplaza el Stop prompt hook anterior.
 * Compara los archivos fuente modificados en esta sesión (session-writes.json)
 * contra los timestamps de los índices en indices/.
 *
 * Si algún fuente fue modificado DESPUÉS del último índice actualizado → avisa.
 *
 * Ventaja vs prompt hook: NO lee la conversación completa.
 * Lee solo el filesystem — O(archivos) en vez de O(tokens de conversación).
 *
 * Exit codes:
 *   0 = ok / nada que reportar
 *   2 = avisar al agente que revise si necesita actualizar índices
 */

const fs = require('fs');
const path = require('path');

const cwd = process.cwd();
const trackerPath = path.join(cwd, '.claude', 'temp', 'session-writes.json');

// Sin writes rastreados → nada que auditar
if (!fs.existsSync(trackerPath)) {
  process.exit(0);
}

let writes = [];
try {
  writes = JSON.parse(fs.readFileSync(trackerPath, 'utf-8'));
} catch {
  process.exit(0);
}

if (writes.length === 0) {
  process.exit(0);
}

// Obtener el timestamp del índice más recientemente modificado
const indexDir = path.join(cwd, 'indices');
let lastIndexMtime = 0;

if (fs.existsSync(indexDir)) {
  try {
    const indexFiles = fs.readdirSync(indexDir).filter(f => f.endsWith('.md'));
    for (const f of indexFiles) {
      const stat = fs.statSync(path.join(indexDir, f));
      if (stat.mtimeMs > lastIndexMtime) lastIndexMtime = stat.mtimeMs;
    }
  } catch { /* fail-open */ }
}

// Verificar si algún fuente fue modificado después del último índice
const newerSourceFiles = [];
for (const filePath of writes) {
  const absPath = path.isAbsolute(filePath) ? filePath : path.join(cwd, filePath);
  try {
    if (!fs.existsSync(absPath)) continue;
    const stat = fs.statSync(absPath);
    if (stat.mtimeMs > lastIndexMtime) {
      newerSourceFiles.push(path.relative(cwd, absPath));
    }
  } catch { /* skip */ }
}

// Limpiar tracker para la próxima sesión
try { fs.unlinkSync(trackerPath); } catch { /* ignore */ }

if (newerSourceFiles.length === 0) {
  process.exit(0);
}

// Avisar al agente
process.stderr.write(
  `\u{1F4CB} SYNC CHECK: ${newerSourceFiles.length} archivo(s) fuente modificados son mas recientes que los indices:\n` +
  newerSourceFiles.map(f => `  - ${f}`).join('\n') + '\n\n' +
  `Si creaste componentes/servicios/directivas NUEVAS, actualiza los indices:\n` +
  `  indices/COMPONENTS.md  — componentes nuevos\n` +
  `  indices/SERVICES.md    — servicios nuevos\n` +
  `  indices/FACADES.md     — facades nuevas\n` +
  `  indices/DIRECTIVES.md  — directivas nuevas\n\n` +
  `  O ejecuta: npm run indices:sync  (regenera USAGE-MAP + secciones auto-generadas)\n\n` +
  `Si solo refactorizaste sin crear elementos nuevos, ignora este aviso.`
);
process.exit(2);
