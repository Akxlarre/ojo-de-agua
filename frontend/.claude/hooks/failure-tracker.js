#!/usr/bin/env node
/**
 * failure-tracker.js — PostToolUseFailure Hook
 *
 * Captures tool execution failures and records them in LESSONS_LEARNED.md
 * with guardrails: max 20 entries, deduplication, automatic rotation.
 *
 * Input (stdin): JSON with tool_name, tool_input, error details
 * Output (stdout): JSON message acknowledging the failure was recorded
 */

const fs = require('fs');
const path = require('path');

const MAX_ENTRIES = 20;
const LESSONS_FILE = path.join(process.cwd(), '.claude', 'temp', 'LESSONS_LEARNED.md');
const TEMP_DIR = path.join(process.cwd(), '.claude', 'temp');

// Read stdin — SEC-04: cap at 10 MB to prevent memory exhaustion.
const MAX_STDIN_BYTES = 10 * 1024 * 1024;
let input = '';
let inputSize = 0;
process.stdin.setEncoding('utf-8');
process.stdin.on('data', (chunk) => {
  inputSize += Buffer.byteLength(chunk, 'utf-8');
  if (inputSize > MAX_STDIN_BYTES) { process.exit(0); }
  input += chunk;
});
process.stdin.on('end', () => {
  try {
    const event = JSON.parse(input);
    const toolName = event.tool_name || 'unknown';
    const toolInput = event.tool_input || {};
    const error = event.error || event.stderr || 'Unknown error';

    // Extract a short signature for dedup (tool + first 80 chars of error)
    const errorSnippet = String(error).replace(/\s+/g, ' ').trim().slice(0, 80);
    const signature = `${toolName}:${errorSnippet}`;

    // Ensure temp dir exists
    if (!fs.existsSync(TEMP_DIR)) {
      fs.mkdirSync(TEMP_DIR, { recursive: true });
    }

    // Read existing lessons
    let existingContent = '';
    let entries = [];
    if (fs.existsSync(LESSONS_FILE)) {
      existingContent = fs.readFileSync(LESSONS_FILE, 'utf-8');
      entries = parseEntries(existingContent);
    }

    // Dedup: skip if same signature already exists
    const isDuplicate = entries.some((e) => e.signature === signature);
    if (isDuplicate) {
      // Update occurrence count on existing entry
      entries = entries.map((e) => {
        if (e.signature === signature) {
          e.occurrences = (e.occurrences || 1) + 1;
          e.lastSeen = new Date().toISOString().split('T')[0];
        }
        return e;
      });
    } else {
      // Add new entry
      const newEntry = {
        date: new Date().toISOString().split('T')[0],
        lastSeen: new Date().toISOString().split('T')[0],
        tool: toolName,
        error: errorSnippet,
        signature,
        occurrences: 1,
        context: typeof toolInput === 'object'
          ? (toolInput.file_path || toolInput.command || '').slice(0, 100)
          : '',
      };
      entries.push(newEntry);
    }

    // Rotation: keep only the most recent MAX_ENTRIES
    if (entries.length > MAX_ENTRIES) {
      entries = entries.slice(entries.length - MAX_ENTRIES);
    }

    // Write back
    const output = renderLessons(entries);
    fs.writeFileSync(LESSONS_FILE, output, 'utf-8');

    // Emit feedback to Claude context
    const msg = isDuplicate
      ? `Failure recorded (duplicate #${entries.find((e) => e.signature === signature)?.occurrences}): ${toolName} — ${errorSnippet}`
      : `New failure recorded: ${toolName} — ${errorSnippet}`;

    process.stdout.write(JSON.stringify({ message: msg }));
  } catch {
    // Silent fail — don't block Claude on tracker errors
    process.exit(0);
  }
});

function parseEntries(content) {
  const entries = [];
  const lines = content.split('\n');
  let current = null;

  for (const line of lines) {
    const match = line.match(
      /^\|\s*`?(\d{4}-\d{2}-\d{2})`?\s*\|\s*`?(.+?)`?\s*\|\s*(.+?)\s*\|\s*(\d+)\s*\|\s*`?(.+?)`?\s*\|\s*(.+?)\s*\|/
    );
    if (match) {
      entries.push({
        date: match[1].trim(),
        tool: match[2].trim(),
        error: match[3].trim(),
        occurrences: parseInt(match[4], 10) || 1,
        signature: match[5].trim(),
        context: match[6].trim(),
        lastSeen: match[1].trim(),
      });
    }
  }
  return entries;
}

function renderLessons(entries) {
  let md = '# Lessons Learned (Auto-generated)\n\n';
  md += '> Max 20 entries. Oldest are rotated out. Duplicates increment count.\n\n';
  md += '| Date | Tool | Error | Count | Signature | Context |\n';
  md += '|------|------|-------|-------|-----------|---------|\n';

  for (const e of entries) {
    md += `| ${e.lastSeen || e.date} | \`${e.tool}\` | ${e.error} | ${e.occurrences} | \`${e.signature}\` | ${e.context} |\n`;
  }

  return md;
}
