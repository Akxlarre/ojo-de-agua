#!/usr/bin/env node
/**
 * error-browser-detector.js — UserPromptSubmit Hook
 *
 * Escanea cada mensaje del usuario buscando patrones de errores de browser/runtime.
 * Si detecta alguno:
 *   1. Escribe los errores detectados en .claude/temp/pending-browser-errors.txt
 *   2. Inyecta additionalContext recordando a Claude que los registre con --record
 *
 * Esto cierra el gap donde el agente recibe errores del browser pero olvida
 * registrarlos en error-value.json mediante error-value-manager.js --record.
 */

import fs from 'fs';
import path from 'path';

const MAX_STDIN_BYTES = 2 * 1024 * 1024;
const PENDING_FILE = path.join(process.cwd(), '.claude', 'temp', 'pending-browser-errors.txt');
const TEMP_DIR = path.join(process.cwd(), '.claude', 'temp');

// Patrones que indican errores de browser/runtime reportados por el usuario
const ERROR_PATTERNS = [
  { re: /ERROR\s+Error:/i,                label: 'JS runtime error' },
  { re: /\b(4\d{2}|5\d{2})\s*\(?\w/,     label: 'HTTP error' },
  { re: /TIMEOUT|timeout.*reached/i,      label: 'timeout' },
  { re: /net::ERR_/i,                     label: 'network error' },
  { re: /Uncaught\s+(TypeError|ReferenceError|SyntaxError)/i, label: 'uncaught exception' },
  { re: /Content Security Policy/i,       label: 'CSP violation' },
  { re: /violates.*Content-Security/i,    label: 'CSP violation' },
  { re: /has not been provided by any.*icon provider/i, label: 'missing icon' },
  { re: /\[ProfilesRepository\].*TIMEOUT/i, label: 'repository timeout' },
  { re: /Transition was aborted/i,        label: 'view transition aborted' },
  { re: /PGRST|postgrest/i,               label: 'PostgREST error' },
];

let stdin = '';
let stdinSize = 0;
process.stdin.setEncoding('utf-8');
process.stdin.on('data', (chunk) => {
  stdinSize += Buffer.byteLength(chunk, 'utf-8');
  if (stdinSize > MAX_STDIN_BYTES) process.exit(0);
  stdin += chunk;
});

process.stdin.on('end', () => {
  try {
    const event = JSON.parse(stdin);
    // El mensaje del usuario puede estar en distintos campos según la versión del harness
    const message = event.message ?? event.prompt ?? event.user_message ?? '';
    if (!message || typeof message !== 'string') process.exit(0);

    // Detectar patrones de error
    const found = ERROR_PATTERNS.filter(({ re }) => re.test(message));
    if (found.length === 0) process.exit(0);

    // Construir snippets de hasta 120 chars por línea que contenga un error
    const lines = message.split('\n');
    const snippets = [];
    for (const { re } of found) {
      const line = lines.find((l) => re.test(l));
      if (line) snippets.push(line.trim().slice(0, 120));
    }

    const labels = [...new Set(found.map((f) => f.label))].join(', ');
    const summary = snippets.join('\n  • ');

    // Escribir flag para que el Stop hook lo recoja
    if (!fs.existsSync(TEMP_DIR)) fs.mkdirSync(TEMP_DIR, { recursive: true });
    const timestamp = new Date().toISOString();
    const entry = `[${timestamp}] ${labels}\n  • ${summary}\n`;
    fs.appendFileSync(PENDING_FILE, entry, 'utf-8');

    // Inyectar recordatorio inmediato en el contexto del agente
    const context =
      `⚠️  ERROR-TRACKER: El usuario acaba de reportar errores de browser (${labels}).\n` +
      `   OBLIGATORIO: Después de investigar y corregir cada error, registrarlo con:\n` +
      `   node scripts/error-value-manager.js --record --pattern "<descripción>" --source browser\n` +
      `   No termines la sesión sin haberlos registrado todos.`;

    process.stdout.write(
      JSON.stringify({
        hookSpecificOutput: {
          hookEventName: 'UserPromptSubmit',
          additionalContext: context,
        },
      }),
    );
    process.exit(0);
  } catch {
    process.exit(0);
  }
});
