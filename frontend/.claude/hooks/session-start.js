#!/usr/bin/env node
/**
 * session-start.js — PreToolUse Hook (todos los tools, matcher: .*)
 *
 * Se ejecuta UNA SOLA VEZ por sesión (primera herramienta usada).
 * Audita context/brief.md al inicio de sesión:
 *
 *   - Si está vacío o es solo plantilla → pide al agente que solicite
 *     al humano el objetivo antes de empezar a escribir código.
 *   - Si tiene contenido pero lleva >7 días sin actualizar → avisa
 *     para que el agente confirme si el objetivo sigue vigente.
 *
 * Por qué al inicio y no solo al Stop (como context-guardian):
 *   Al Stop el daño ya ocurrió — el agente pasó la sesión divagando.
 *   Detectarlo al inicio permite corregir antes de escribir código.
 *
 * Nunca bloquea (exit 0 siempre). Inyecta via additionalContext.
 */

'use strict';

const fs   = require('fs');
const path = require('path');
const os   = require('os');

const cwd       = process.cwd();
const sessionId = process.env.CLAUDE_SESSION_ID || 'default';
const flagPath  = path.join(os.tmpdir(), `koa-session-start-${sessionId}.flag`);

// Solo ejecutar una vez por sesión
if (fs.existsSync(flagPath)) {
  process.exit(0);
}

// Drena stdin antes de escribir el flag y responder
let data = '';
process.stdin.on('data', chunk => { data += chunk; });
process.stdin.on('end', () => {
  try {
    fs.writeFileSync(flagPath, new Date().toISOString());

    const briefPath = path.join(cwd, 'context', 'brief.md');
    if (!fs.existsSync(briefPath)) process.exit(0);

    const raw      = fs.readFileSync(briefPath, 'utf-8');
    const stripped = raw.replace(/<!--[\s\S]*?-->/g, '').trim();
    let message    = null;

    if (stripped.length < 80) {
      // Brief vacío o solo plantilla sin contenido real
      message =
        '⚠️  BRIEF VACÍO: context/brief.md no tiene contenido real.\n' +
        '   Antes de empezar: pregunta al humano cuál es el objetivo de esta sesión\n' +
        '   y pídele que actualice context/brief.md (campo last_updated + objetivo).\n' +
        '   Un brief claro evita exploración innecesaria y reduce tokens desperdiciados.';
    } else {
      // Brief con contenido — verificar frescura por last_updated
      const match = raw.match(/\*\*last_updated:\*\*\s*(\d{4}-\d{2}-\d{2})/);
      if (match) {
        const daysSince = Math.floor((Date.now() - new Date(match[1]).getTime()) / 86400000);
        if (daysSince > 7) {
          message =
            `📅 BRIEF DESACTUALIZADO (${daysSince}d): context/brief.md lleva ${daysSince} días sin actualizar (${match[1]}).\n` +
            `   Confirma con el humano si el objetivo de sesión sigue vigente antes de empezar.`;
        }
      }
    }

    if (!message) process.exit(0);

    process.stdout.write(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        additionalContext: message
      }
    }));
    process.exit(0);
  } catch {
    process.exit(0); // fail-open siempre
  }
});
