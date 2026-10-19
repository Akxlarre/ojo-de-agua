#!/usr/bin/env node
/**
 * bash-guard.js — PreToolUse Hook (Bash)
 *
 * Protege contra:
 *   1. Creación de archivos .ts/.html/.scss via Bash (debe usar Edit/Write)
 *   2. Operaciones destructivas sobre directorios críticos del proyecto
 *   3. Instalación/desinstalación de dependencias sin confirmación explícita
 *
 * Exit codes:
 *   0 = permitir el comando
 *   2 = bloquear el comando
 */

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
    const command = input.tool_input?.command || '';

    // SEC-07: Normalize whitespace (tabs, multiple spaces) before matching
    // to prevent bypass via tab characters or non-standard spacing.
    const normalizedCmd = command.replace(/\t/g, ' ').replace(/  +/g, ' ');

    // ═══════════════════════════════════════════════════════════════════════
    // 1. Bloquear creación de archivos fuente via Bash
    // ═══════════════════════════════════════════════════════════════════════
    // SEC-07: Use both original and normalized command. Patterns now also catch
    // heredoc redirections (<<EOF) and process substitution variants.
    const fileCreationPatterns = [
      /(?:cat|echo|printf|tee)\b[^|]*>\s*.*src\/app\/.*\.(?:ts|html|scss)/,
      />\s*.*src\/app\/.*\.(?:ts|html|scss)/,
      /(?:cat|echo|printf|tee)\b[^|]*>\s*.*supabase\/migrations\/.*\.sql/,
      />\s*.*supabase\/migrations\/.*\.sql/,
    ];

    for (const pattern of fileCreationPatterns) {
      if (pattern.test(command) || pattern.test(normalizedCmd)) {
        process.stderr.write(
          `\u{1F6AB} BASH GUARD: No crear archivos de codigo fuente mediante Bash.\n` +
          `Usa las herramientas Edit o Write para crear y modificar archivos .ts, .html, .scss y .sql.\n` +
          `Esto permite que los guardrails arquitectonicos validen tu codigo.`
        );
        process.exit(2);
      }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // 2. Bloquear operaciones destructivas en directorios críticos
    // ═══════════════════════════════════════════════════════════════════════
    // SEC-07: Patterns now match -rf, -fr, -r -f (any order) and double-dash
    // separator (rm -rf -- src/app) to prevent flag-reordering bypasses.
    const destructivePatterns = [
      {
        re: /\brm\b.*-[a-zA-Z]*r[a-zA-Z]*\b.*(?:src\/app|\.claude|indices|supabase)/,
        msg: 'Eliminacion recursiva de directorio critico',
      },
      {
        re: /\brm\b.*(?:\.claude\/hooks|\.claude\/settings|architect\.js)/,
        msg: 'Eliminacion de archivos del sistema de guardrails',
      },
      {
        re: />\s*(?:\.claude\/settings(?:\.local)?\.json|\.claude\/hooks\/)/,
        msg: 'Sobreescritura de configuracion de guardrails',
      },
    ];

    for (const { re, msg } of destructivePatterns) {
      if (re.test(command) || re.test(normalizedCmd)) {
        process.stderr.write(
          `\u{1F6E1}\u{FE0F} BASH GUARD: Operacion destructiva bloqueada.\n` +
          `Razon: ${msg}\n` +
          `Si realmente necesitas hacer esto, pide al humano que lo ejecute manualmente.`
        );
        process.exit(2);
      }
    }

    // ═══════════════════════════════════════════════════════════════════════
    // 3. SUPPLY CHAIN & EXECUTION GUARD (Ciberseguridad)
    // ═══════════════════════════════════════════════════════════════════════
    const securityPatterns = [
      { re: /(?:npm|yarn|pnpm|pip|gem)\s+(?:install|add|i|uninstall|rm)\s+[^-\s]+/, msg: 'Mutacion de dependencias. Pide al humano que apruebe e instale paquetes por seguridad.' },
      { re: /(?:curl|wget)\s+/, msg: 'Ejecucion de comandos de red (curl/wget). Descargas arbitrarias bloqueadas por seguridad.' },
      { re: /node\s+-e\s+.*(?:http|https)/, msg: 'Ejecucion de red inline con Node.js' }
    ];

    for (const { re, msg } of securityPatterns) {
      if (re.test(command) || re.test(normalizedCmd)) {
        process.stderr.write(
          `\u{1F6A8} BASH GUARD (CYBERSECURITY): Operacion bloqueada por seguridad.\n` +
          `Razon: ${msg}\n` +
          `Las politicas de Agentic Security impiden la instalacion de paquetes no verificados o descargas directas.\n` +
          `Si esto es requerido, pide al humano que lo ejecute en su terminal.`
        );
        process.exit(2);
      }
    }

    process.exit(0);
  } catch {
    // Fail-open: si el hook falla, permitir el comando
    process.exit(0);
  }
});
