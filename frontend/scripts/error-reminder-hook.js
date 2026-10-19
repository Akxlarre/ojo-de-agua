#!/usr/bin/env node
/**
 * error-reminder-hook.js — Stop Hook
 *
 * Comprueba si error-browser-detector.js dejó errores pendientes de registrar
 * en .claude/temp/pending-browser-errors.txt.
 *
 * Si existen → emite un recordatorio visible al agente vía stderr (exit 2)
 *              y borra el archivo para no repetirlo en la próxima sesión.
 * Si no hay nada pendiente → sale silenciosamente (exit 0).
 */

import fs from 'fs';
import path from 'path';

const PENDING_FILE = path.join(process.cwd(), '.claude', 'temp', 'pending-browser-errors.txt');

if (!fs.existsSync(PENDING_FILE)) process.exit(0);

let content = '';
try {
  content = fs.readFileSync(PENDING_FILE, 'utf-8').trim();
} catch {
  process.exit(0);
}

if (!content) {
  try { fs.unlinkSync(PENDING_FILE); } catch { /* ignore */ }
  process.exit(0);
}

// Borrar el archivo antes de salir para no repetir en próxima sesión
try { fs.unlinkSync(PENDING_FILE); } catch { /* ignore */ }

process.stderr.write(
  `🔴 ERROR-REMINDER: Esta sesión tuvo errores de browser reportados por el usuario\n` +
  `   que pueden NO haber sido registrados en error-value.json.\n\n` +
  `   Errores detectados:\n` +
  content.split('\n').map((l) => `   ${l}`).join('\n') +
  `\n\n` +
  `   Si ya los registraste con --record, ignora este aviso.\n` +
  `   Si no, hazlo ahora:\n` +
  `   node scripts/error-value-manager.js --record --pattern "<descripción>" --source browser\n`,
);
process.exit(2);
