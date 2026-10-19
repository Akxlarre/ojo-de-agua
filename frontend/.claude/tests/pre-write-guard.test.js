#!/usr/bin/env node
/**
 * pre-write-guard.test.js — Contract tests del hook principal
 *
 * Verifica que el ARCHITECT GUARD bloquee correctamente cada regla.
 * Usa node:test nativo (Node 18+) y child_process para simular el hook.
 */

const { test, describe } = require('node:test');
const assert = require('node:assert/strict');
const { execSync, spawnSync } = require('child_process');
const path = require('path');

const HOOK = path.resolve(__dirname, '..', 'hooks', 'pre-write-guard.js');

/**
 * Ejecuta el hook con un TOOL_INPUT simulado.
 * @param {object} input - { tool_name, tool_input: { file_path, content|new_string } }
 * @returns {{ exitCode: number, stdout: string, stderr: string }}
 */
function runHook(input) {
  const result = spawnSync('node', [HOOK], {
    input: JSON.stringify(input),
    encoding: 'utf8',
    env: { ...process.env, CLAUDE_SESSION_ID: 'test-session-' + Date.now() }
  });
  return {
    exitCode: result.status,
    stdout: result.stdout || '',
    stderr: result.stderr || ''
  };
}

function makeInput(filePath, content, toolName = 'Write') {
  return {
    tool_name: toolName,
    tool_input: { file_path: filePath, content, new_string: content }
  };
}

// ─── FILE PROTECTOR tests ───────────────────────────────────────────────────
describe('FILE PROTECTOR', () => {
  test('bloquea edicion a .claude/hooks/', () => {
    const r = runHook(makeInput('/project/.claude/hooks/pre-write-guard.js', 'console.log("x")'));
    assert.equal(r.exitCode, 2);
    assert.ok(r.stderr.includes('FILE PROTECTOR') || r.stderr.includes('guardrails'));
  });

  test('bloquea edicion a scripts/architect.js', () => {
    const r = runHook(makeInput('/project/scripts/architect.js', 'const x = 1'));
    assert.equal(r.exitCode, 2);
  });
});

// ─── ARCHITECT GUARD tests ──────────────────────────────────────────────────
describe('ARCHITECT GUARD — Angular', () => {
  const featurePath = '/project/src/app/features/dashboard/dashboard.component.ts';
  const sharedPath = '/project/src/app/shared/components/kpi-card/kpi-card.component.ts';
  const htmlPath = '/project/src/app/features/dashboard/dashboard.component.html';

  test('bloquea *ngIf en template TypeScript', () => {
    const r = runHook(makeInput(featurePath, 'template: `<div *ngIf="cond">x</div>`'));
    assert.equal(r.exitCode, 2);
    assert.ok(r.stderr.includes('ngIf'));
  });

  test('permite @if en template TypeScript', () => {
    const r = runHook(makeInput(featurePath, 'template: `@if (cond) { <div>x</div> }`'));
    // No debe bloquear por ngIf (puede bloquear por OnPush si no lo tiene)
    assert.ok(r.exitCode !== 2 || !r.stderr.includes('ngIf'));
  });

  test('bloquea @Input() decorator', () => {
    const r = runHook(makeInput(featurePath, '@Input() public value: string;'));
    assert.equal(r.exitCode, 2);
    assert.ok(r.stderr.includes('@Input'));
  });

  test('bloquea @Output() decorator', () => {
    const r = runHook(makeInput(featurePath, '@Output() public changed = new EventEmitter();'));
    assert.equal(r.exitCode, 2);
    assert.ok(r.stderr.includes('@Output'));
  });

  test('bloquea color Tailwind hardcodeado', () => {
    const r = runHook(makeInput(featurePath, '<div class="text-red-500 bg-blue-200">x</div>'));
    assert.equal(r.exitCode, 2);
    assert.ok(r.stderr.includes('hardcodeado') || r.stderr.includes('ARCHITECT'));
  });

  test('bloquea inject de Facade en Dumb component (shared/)', () => {
    const r = runHook(makeInput(sharedPath,
      'readonly facade = inject(AuthFacade); template: `<div>x</div>`',
      'Write'
    ));
    assert.equal(r.exitCode, 2);
    assert.ok(r.stderr.includes('Dumb') || r.stderr.includes('Facade'));
  });

  test('bloquea @angular/animations', () => {
    const r = runHook(makeInput(featurePath, "import { animate } from '@angular/animations';"));
    assert.equal(r.exitCode, 2);
  });

  test('bloquea inject(MessageService) en componentes UI', () => {
    const r = runHook(makeInput(featurePath, 'inject(MessageService)'));
    assert.equal(r.exitCode, 2);
    assert.ok(r.stderr.includes('MessageService') || r.stderr.includes('ToastService'));
  });
});

describe('ARCHITECT GUARD — A11Y', () => {
  const htmlPath = '/project/src/app/features/dashboard/dashboard.component.html';

  test('bloquea <app-icon> sin aria-label', () => {
    const r = runHook(makeInput(htmlPath, '<app-icon name="trash" />'));
    assert.equal(r.exitCode, 2);
    assert.ok(r.stderr.includes('A11Y-01') || r.stderr.includes('aria-label'));
  });

  test('permite <app-icon> con aria-label', () => {
    const r = runHook(makeInput(htmlPath, '<app-icon name="trash" [attr.aria-label]="'Eliminar'" />'));
    // No debe bloquear por A11Y-01
    assert.ok(r.exitCode !== 2 || !r.stderr.includes('A11Y-01'));
  });

  test('bloquea <p-table> sin aria-label ni caption', () => {
    const r = runHook(makeInput(htmlPath, '<p-table [value]="data()"></p-table>'));
    assert.equal(r.exitCode, 2);
    assert.ok(r.stderr.includes('A11Y-02') || r.stderr.includes('p-table'));
  });
});

describe('ARCHITECT GUARD — SQL', () => {
  const migrationPath = '/project/supabase/migrations/20240101000000_auth_create_profiles.sql';

  test('bloquea CREATE TABLE sin RLS', () => {
    const r = runHook(makeInput(migrationPath, 'CREATE TABLE public.users (id uuid PRIMARY KEY);'));
    assert.equal(r.exitCode, 2);
    assert.ok(r.stderr.includes('RLS') || r.stderr.includes('ROW LEVEL SECURITY'));
  });

  test('permite CREATE TABLE con RLS', () => {
    const r = runHook(makeInput(migrationPath,
      'CREATE TABLE public.users (id uuid PRIMARY KEY);\nALTER TABLE public.users ENABLE ROW LEVEL SECURITY;'
    ));
    assert.ok(r.exitCode !== 2 || !r.stderr.includes('RLS'));
  });
});

describe('ARCHITECT GUARD — ARCH-11', () => {
  test('bloquea edicion manual de supabase.types.ts', () => {
    const r = runHook(makeInput(
      '/project/src/app/core/models/supabase.types.ts',
      'export type Database = {};'
    ));
    assert.equal(r.exitCode, 2);
    assert.ok(r.stderr.includes('ARCH-11') || r.stderr.includes('AUTO-GENERADO'));
  });
});
