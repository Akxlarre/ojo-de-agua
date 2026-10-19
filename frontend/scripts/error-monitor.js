#!/usr/bin/env node
/**
 * error-monitor.js — Wrapper de proceso transparente
 *
 * Intercala cualquier comando (ng serve, ng build, etc.) sin modificar Angular.
 * Lee stdout/stderr del proceso hijo, los reimprime intactos al terminal,
 * y en paralelo detecta patrones de error para actualizar error-value.json.
 *
 * Uso en package.json:
 *   "start": "node scripts/error-monitor.js ng serve"
 *   "build": "node scripts/error-monitor.js ng build"
 *
 * El usuario nunca nota la diferencia — es completamente transparente.
 */

import { spawn } from 'child_process';
import { recordError } from './error-value-manager.js';

// Elimina secuencias ANSI (colores, cursores) del output del terminal
const ANSI_RE = /\x1B\[[0-9;]*[a-zA-Z]|\x1B\][^\x07]*\x07/g;
function stripAnsi(str) { return str.replace(ANSI_RE, ''); }

// Solo procesar líneas que parecen errores reales — ignora líneas informativas
const NOISE_PATTERNS = [
  /^\s*$/,                         // vacías
  /^[❯✔◐◑◒◓⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏►]\s/,   // spinners / progress
  /^Building\.\.\./i,
  /^Watch mode/i,
  /^Application bundle generation/i,
  /^\s*\d+\s*│/,                   // líneas de código fuente del stack trace
  /^[~╵└─]+$/,                     // decoradores de subrayado en stack trace
  /^\s*at /,                       // stack frames JS
];

function isNoiseLine(line) {
  return NOISE_PATTERNS.some((re) => re.test(line));
}

const args = process.argv.slice(2);
if (args.length === 0) {
  console.error('error-monitor: especifica el comando a ejecutar (ej: ng serve)');
  process.exit(1);
}

const [cmd, ...cmdArgs] = args;

const child = spawn(cmd, cmdArgs, {
  stdio: ['inherit', 'pipe', 'pipe'],
  shell: process.platform === 'win32',
  env: process.env,
});

// Buffer acumulado para detectar errores que pueden llegar en múltiples chunks
let stdoutBuf = '';
let stderrBuf = '';

function flushAndScan(buf, isStderr) {
  // Escanear línea a línea para no procesar mensajes parciales
  const lines = buf.split('\n');
  const incomplete = lines.pop(); // última línea posiblemente incompleta

  for (const line of lines) {
    if (line.trim()) scanLine(line, isStderr ? 'cli' : 'cli');
  }

  return incomplete;
}

function scanLine(line, source) {
  const clean = stripAnsi(line).trim();
  if (!clean || isNoiseLine(clean)) return;

  // Solo procesar si la línea parece un error real
  const looksLikeError = /error|warning|failed|TS\d{4}|PGRST|RLS|401|403|500|ARCH-|Exception|cannot|Cannot|undefined|null ref/i.test(clean);
  if (!looksLikeError) return;

  try {
    const result = recordError({ pattern: clean, source });
    if (result) {
      const priority = result.weight >= 4 ? '🔴' : result.weight >= 3 ? '🟠' : '🟡';
      // Solo loguear en stderr del monitor para no contaminar stdout del proceso
      if (result.isNew) {
        process.stderr.write(`\n${priority} [KOA-LEARN] Nuevo error: [${result.code}] — registrado en error-value.json\n`);
      } else if (result.count % 5 === 0) {
        // Avisar cada 5 ocurrencias para no spamear
        process.stderr.write(`\n${priority} [KOA-LEARN] [${result.code}] ha ocurrido ${result.count} veces — prioridad creciente\n`);
      }
    }
  } catch {
    // fail-open: nunca interrumpir el proceso hijo
  }
}

child.stdout.on('data', (data) => {
  const text = data.toString();
  process.stdout.write(text); // reimpresión transparente
  stdoutBuf += text;
  stdoutBuf = flushAndScan(stdoutBuf, false) || '';
});

child.stderr.on('data', (data) => {
  const text = data.toString();
  process.stderr.write(text); // reimpresión transparente
  stderrBuf += text;
  stderrBuf = flushAndScan(stderrBuf, true) || '';
});

child.on('close', (code) => {
  // Procesar cualquier remanente en buffers
  if (stdoutBuf.trim()) scanLine(stdoutBuf, 'cli');
  if (stderrBuf.trim()) scanLine(stderrBuf, 'cli');

  process.exit(code ?? 0);
});

child.on('error', (err) => {
  console.error(`error-monitor: no pudo iniciar el proceso — ${err.message}`);
  process.exit(1);
});

// Propagar señales al proceso hijo para que Ctrl+C funcione normalmente
for (const sig of ['SIGINT', 'SIGTERM']) {
  process.on(sig, () => {
    child.kill(sig);
  });
}
