#!/usr/bin/env node
/**
 * error-learning-hook.js — PostCompact Hook (registrado en settings.json)
 *
 * Lee error-value.json y, si hay errores críticos (weight >= 3 o count >= 5),
 * los inyecta en el contexto del agente como "Prioridades de Sesión".
 *
 * Así Claude arranca cada sesión ya sabiendo los errores más frecuentes
 * sin que el usuario tenga que mencionarlos de nuevo.
 *
 * Ubicado en scripts/ porque .claude/hooks/ es protegido por el File Protector.
 */

'use strict';

const fs   = require('fs');
const path = require('path');

const cwd              = process.cwd();
const ERROR_VALUE_PATH = path.join(cwd, 'error-value.json');

const WEIGHT_THRESHOLD = 3;
const COUNT_THRESHOLD  = 5;
const MAX_INJECT       = 8;

let stdin = '';
process.stdin.setEncoding('utf-8');
process.stdin.on('data', (c) => { stdin += c; });
process.stdin.on('end', () => {
  try {
    if (!fs.existsSync(ERROR_VALUE_PATH)) process.exit(0);

    const map     = JSON.parse(fs.readFileSync(ERROR_VALUE_PATH, 'utf-8'));
    const errors  = Object.values(map.errors || {});
    const critical = errors
      .filter((e) => e.weight >= WEIGHT_THRESHOLD || e.count >= COUNT_THRESHOLD)
      .sort((a, b) => b.weight * b.count - a.weight * a.count)
      .slice(0, MAX_INJECT);

    if (critical.length === 0) process.exit(0);

    const lines = critical.map((e) => {
      const icon = e.weight >= 5 ? '🔴' : e.weight >= 4 ? '🟠' : '🟡';
      return `  ${icon} [${e.code}] w=${e.weight} ×${e.count} — ${e.hint || e.summary || (e.pattern || '').slice(0, 80)}`;
    });

    const message =
      `🧠 ERROR LEARNING — Errores frecuentes en este proyecto (error-value.json):\n` +
      `   Tenlos en cuenta al sugerir código o al recibir errores del usuario:\n\n` +
      lines.join('\n') +
      `\n\n   ℹ️  Si el usuario anuncia un error en el chat, ejecuta:\n` +
      `   node scripts/error-value-manager.js --record --pattern "..." --source browser|cli|backend`;

    process.stdout.write(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PostCompact',
        additionalContext: message,
      },
    }));
    process.exit(0);
  } catch {
    process.exit(0);
  }
});
