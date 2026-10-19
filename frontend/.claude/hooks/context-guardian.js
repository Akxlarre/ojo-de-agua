#!/usr/bin/env node
/**
 * context-guardian.js — Stop Hook (command)
 *
 * Vigila la frescura de los archivos de contexto semántico.
 * Complementa sync-check.js (que audita índices de código) con
 * una auditoría de la capa de contexto humano (context/).
 *
 * Checks:
 *   1. context/brief.md → last_updated > 7 días: avisar que puede estar desactualizado
 *   2. context/learnings.md → sin actualizar en >14 días: sugerir registrar aprendizajes
 *
 * Exit codes:
 *   0 = ok / nada que reportar
 *   2 = avisar al agente (stderr) sobre contexto desactualizado
 */

const fs = require('fs');
const path = require('path');

const cwd = process.cwd();
const warnings = [];

// ─── Check 1: brief.md staleness ──────────────────────────────────────────
const briefPath = path.join(cwd, 'context', 'brief.md');
if (fs.existsSync(briefPath)) {
  try {
    const content = fs.readFileSync(briefPath, 'utf-8');
    const match = content.match(/\*\*last_updated:\*\*\s*(\d{4}-\d{2}-\d{2})/);
    if (match) {
      const daysSince = Math.floor((Date.now() - new Date(match[1]).getTime()) / 86400000);
      if (daysSince > 7) {
        warnings.push(
          `\u{1F4C5} BRIEF DESACTUALIZADO: context/brief.md fue actualizado hace ${daysSince} dias (${match[1]}).\n` +
          `   Pide al humano que actualice last_updated y el objetivo antes de la proxima sesion.`
        );
      }
    }
  } catch { /* fail-open */ }
}

// ─── Check 2: learnings.md sin actualizar ─────────────────────────────────
const learningsPath = path.join(cwd, 'context', 'learnings.md');
if (fs.existsSync(learningsPath)) {
  try {
    const stat = fs.statSync(learningsPath);
    const daysSince = Math.floor((Date.now() - stat.mtimeMs) / 86400000);
    if (daysSince > 14) {
      warnings.push(
        `\u{1F4DA} LEARNINGS: context/learnings.md no ha sido actualizado en ${daysSince} dias.\n` +
        `   Si aprendiste algo esta sesion (quirks de APIs, terminologia del cliente,\n` +
        `   decisiones con motivo), considera registrarlo en context/learnings.md.`
      );
    }
  } catch { /* fail-open */ }
}

if (warnings.length === 0) {
  process.exit(0);
}

process.stderr.write(
  '\u2500\u2500\u2500 Context Guardian \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n' +
  warnings.join('\n\n') + '\n' +
  '\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\n'
);
process.exit(2);
