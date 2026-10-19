#!/usr/bin/env node
/**
 * write-tracker.js — PostToolUse Hook (Edit|Write|MultiEdit)
 *
 * Rastrea qué archivos fuente Angular fueron modificados en esta sesión.
 * Escribe la lista en .claude/temp/session-writes.json.
 *
 * El sync-check.js (Stop hook) usa esta lista para auditar si los
 * índices necesitan actualización — sin leer toda la conversación.
 * Ventaja: O(archivos) vs O(tokens de conversación).
 */

const fs = require('fs');
const path = require('path');

// SEC-04: Limit stdin to 10 MB to prevent memory exhaustion.
const MAX_STDIN_BYTES = 10 * 1024 * 1024;
let data = '';
let dataSize = 0;
process.stdin.on('data', chunk => {
  dataSize += chunk.length;
  if (dataSize > MAX_STDIN_BYTES) { process.exit(0); }
  data += chunk;
});
process.stdin.on('end', () => {
  try {
    const input = JSON.parse(data);
    const filePath = (input.tool_input?.file_path || input.tool_input?.path || '').replace(/\\/g, '/');

    // Solo rastrear archivos fuente Angular — no specs, no hooks, no índices
    const isSourceFile =
      filePath.includes('src/app/') &&
      !filePath.endsWith('.spec.ts') &&
      (filePath.endsWith('.ts') || filePath.endsWith('.html') || filePath.endsWith('.scss'));

    if (!isSourceFile) {
      process.exit(0);
    }

    const tempDir = path.join(process.cwd(), '.claude', 'temp');
    const trackerPath = path.join(tempDir, 'session-writes.json');

    if (!fs.existsSync(tempDir)) {
      fs.mkdirSync(tempDir, { recursive: true });
    }

    let writes = [];
    if (fs.existsSync(trackerPath)) {
      try { writes = JSON.parse(fs.readFileSync(trackerPath, 'utf-8')); } catch { writes = []; }
    }

    if (!writes.includes(filePath)) {
      writes.push(filePath);
      fs.writeFileSync(trackerPath, JSON.stringify(writes, null, 2));
    }
  } catch {
    // fail-open — nunca bloquear el flujo de trabajo
  }
  process.exit(0);
});
