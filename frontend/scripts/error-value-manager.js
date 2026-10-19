#!/usr/bin/env node
/**
 * error-value-manager.js
 *
 * Módulo compartido Y herramienta CLI para gestionar error-value.json.
 *
 * Como módulo (import):
 *   import { recordError, readErrorMap, getTopErrors } from './error-value-manager.js';
 *
 * Como CLI (node scripts/error-value-manager.js --help):
 *   --record          Registrar un error (requiere --pattern)
 *   --source          Origen: cli | browser | backend (default: cli)
 *   --pattern         Texto del error (requerido con --record)
 *   --summary         Descripción legible (opcional)
 *   --list            Listar el mapa de calor actual
 *   --top N           Top N errores por peso×count
 *
 * El CLI es llamado por Claude directamente cuando el usuario anuncia un error en el chat.
 */

import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { matchError } from './error-catalog.js';

const ANSI_RE = /\x1B\[[0-9;]*[a-zA-Z]|\x1B\][^\x07]*\x07/g;
function stripAnsi(str) { return str.replace(ANSI_RE, ''); }

const PROJECT_ROOT = process.cwd();
const ERROR_VALUE_PATH = path.join(PROJECT_ROOT, 'error-value.json');

const MAX_UNIQUE_ERRORS = 50;
const SHARING_OPT_IN_FLAG = path.join(PROJECT_ROOT, '.koa', 'sharing-enabled');

// ── Helpers ──────────────────────────────────────────────────────────────────

function today() {
  return new Date().toISOString().split('T')[0];
}

function projectId() {
  const pkgPath = path.join(PROJECT_ROOT, 'package.json');
  if (!fs.existsSync(pkgPath)) return 'unknown';
  const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf-8'));
  return crypto.createHash('sha256').update(pkg.name || 'unnamed').digest('hex').slice(0, 12);
}

// ── Core CRUD ─────────────────────────────────────────────────────────────────

export function readErrorMap() {
  if (!fs.existsSync(ERROR_VALUE_PATH)) {
    return {
      schema_version: 1,
      project_id: projectId(),
      updated_at: today(),
      errors: {},
      memory: { max_unique: MAX_UNIQUE_ERRORS, eviction_policy: 'least_recent_low_weight' },
    };
  }
  try {
    return JSON.parse(fs.readFileSync(ERROR_VALUE_PATH, 'utf-8'));
  } catch {
    return { schema_version: 1, project_id: projectId(), updated_at: today(), errors: {}, memory: { max_unique: MAX_UNIQUE_ERRORS, eviction_policy: 'least_recent_low_weight' } };
  }
}

function writeErrorMap(map) {
  map.updated_at = today();
  fs.writeFileSync(ERROR_VALUE_PATH, JSON.stringify(map, null, 2), 'utf-8');
}

function evict(map) {
  const keys = Object.keys(map.errors);
  if (keys.length <= MAX_UNIQUE_ERRORS) return map;

  // Ordenar por score ascendente (menos crítico primero) para evictar
  const scored = keys.map((k) => ({
    key: k,
    score: map.errors[k].count * map.errors[k].weight,
    lastSeen: map.errors[k].last_seen,
  }));

  scored.sort((a, b) => a.score - b.score || a.lastSeen.localeCompare(b.lastSeen));

  const toRemove = scored.slice(0, keys.length - MAX_UNIQUE_ERRORS);
  for (const item of toRemove) {
    delete map.errors[item.key];
  }
  return map;
}

/**
 * Registra un error en el mapa de calor.
 * @param {object} opts
 * @param {string} opts.pattern  - Texto crudo del error
 * @param {string} opts.source   - 'cli' | 'browser' | 'backend'
 * @param {string} [opts.summary] - Descripción legible
 * @returns {{ code: string, isNew: boolean, count: number, weight: number }}
 */
export function recordError({ pattern, source = 'cli', summary = '' }) {
  const clean = stripAnsi(pattern).trim();
  if (!clean) return null;
  pattern = clean;
  const catalog = matchError(pattern);
  const code = catalog?.code || `UNKNOWN-${crypto.createHash('md5').update(pattern.slice(0, 60)).digest('hex').slice(0, 6).toUpperCase()}`;
  const weight = catalog?.weight ?? 2;
  const hint = catalog?.hint ?? '';

  const map = readErrorMap();
  const isNew = !map.errors[code];

  if (isNew) {
    map.errors[code] = {
      code,
      pattern: pattern.replace(/\s+/g, ' ').trim().slice(0, 120),
      source: catalog?.source || source,
      category: catalog?.category || 'unknown',
      weight,
      hint,
      count: 1,
      first_seen: today(),
      last_seen: today(),
      summary: summary || hint,
    };
  } else {
    map.errors[code].count += 1;
    map.errors[code].last_seen = today();
    if (summary) map.errors[code].summary = summary;
  }

  evict(map);
  writeErrorMap(map);

  return { code, isNew, count: map.errors[code].count, weight };
}

/**
 * Retorna los N errores más críticos (weight * count) para inyectar en contexto.
 * @param {number} n
 * @param {number} minWeight - Solo incluir si weight >= minWeight
 * @returns {Array}
 */
export function getTopErrors(n = 10, minWeight = 2) {
  const map = readErrorMap();
  return Object.values(map.errors)
    .filter((e) => e.weight >= minWeight)
    .sort((a, b) => b.weight * b.count - a.weight * a.count)
    .slice(0, n);
}

/**
 * Retorna errores con weight >= threshold O count >= countThreshold (prioridad alta).
 */
export function getCriticalErrors({ weightThreshold = 3, countThreshold = 5 } = {}) {
  const map = readErrorMap();
  return Object.values(map.errors).filter(
    (e) => e.weight >= weightThreshold || e.count >= countThreshold
  );
}

// ── CLI entrypoint ────────────────────────────────────────────────────────────

function cliHelp() {
  console.log(`
error-value-manager.js — Mapa de calor de errores del proyecto

Uso:
  node scripts/error-value-manager.js --record --pattern "TS2345: ..." [--source cli] [--summary "..."]
  node scripts/error-value-manager.js --list
  node scripts/error-value-manager.js --top 5

Opciones:
  --record          Registrar un error
  --pattern  TEXT   Texto del error (requerido con --record)
  --source   TEXT   cli | browser | backend (default: cli)
  --summary  TEXT   Descripción legible
  --list            Mostrar mapa de calor completo
  --top      N      Top N errores críticos (por peso × cuenta)
  --help            Esta ayuda
  `);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);
  const get = (flag) => {
    const i = args.indexOf(flag);
    return i !== -1 ? args[i + 1] : null;
  };
  const has = (flag) => args.includes(flag);

  if (has('--help') || args.length === 0) {
    cliHelp();
    process.exit(0);
  }

  if (has('--record')) {
    const pattern = get('--pattern');
    if (!pattern) {
      console.error('❌ --pattern es requerido con --record');
      process.exit(1);
    }
    const result = recordError({
      pattern,
      source: get('--source') || 'cli',
      summary: get('--summary') || '',
    });
    const icon = result.isNew ? '🆕' : '🔁';
    console.log(`${icon} [${result.code}] count=${result.count} weight=${result.weight}`);
    process.exit(0);
  }

  if (has('--list')) {
    const map = readErrorMap();
    const entries = Object.values(map.errors).sort((a, b) => b.weight * b.count - a.weight * a.count);
    if (entries.length === 0) {
      console.log('No hay errores registrados aún.');
    } else {
      console.log(`\n📊 Error Map — ${map.project_id} (${map.updated_at})\n`);
      for (const e of entries) {
        console.log(`  [${e.code}] w=${e.weight} ×${e.count} | ${e.summary || e.pattern.slice(0, 60)}`);
      }
    }
    process.exit(0);
  }

  if (has('--top')) {
    const n = parseInt(get('--top') || '5', 10);
    const top = getTopErrors(n);
    if (top.length === 0) {
      console.log('No hay errores con peso suficiente.');
    } else {
      console.log(`\n🔥 Top ${n} errores críticos:\n`);
      for (const e of top) {
        console.log(`  [${e.code}] w=${e.weight} ×${e.count} — ${e.hint || e.summary}`);
      }
    }
    process.exit(0);
  }

  cliHelp();
  process.exit(1);
}
