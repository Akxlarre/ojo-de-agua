#!/usr/bin/env node
/**
 * bash-guard.test.js — Contract tests del hook bash-guard
 */

const { test, describe } = require('node:test');
const assert = require('node:assert/strict');
const { spawnSync } = require('child_process');
const path = require('path');

const HOOK = path.resolve(__dirname, '..', 'hooks', 'bash-guard.js');

function runHook(cmd) {
  const input = JSON.stringify({ tool_name: 'Bash', tool_input: { command: cmd } });
  const result = spawnSync('node', [HOOK], {
    input,
    encoding: 'utf8',
    env: { ...process.env, TOOL_INPUT: input }
  });
  return { exitCode: result.status, stderr: result.stderr || '' };
}

describe('BASH GUARD — creacion de archivos', () => {
  test('bloquea creacion de .ts via touch', () => {
    const r = runHook('touch src/app/features/dashboard/new.component.ts');
    assert.equal(r.exitCode, 2);
  });

  test('bloquea creacion de .html via touch', () => {
    const r = runHook('touch src/app/shared/components/foo.component.html');
    assert.equal(r.exitCode, 2);
  });

  test('bloquea creacion de .scss via touch', () => {
    const r = runHook('touch src/app/core/styles/foo.scss');
    assert.equal(r.exitCode, 2);
  });

  test('permite comandos ng build', () => {
    const r = runHook('ng build --configuration production');
    assert.ok(r.exitCode !== 2);
  });

  test('permite npm run test', () => {
    const r = runHook('npm run test:ci');
    assert.ok(r.exitCode !== 2);
  });
});

describe('BASH GUARD — operaciones destructivas', () => {
  test('bloquea rm -rf en src/app', () => {
    const r = runHook('rm -rf src/app/features/dashboard');
    assert.equal(r.exitCode, 2);
  });

  test('bloquea rm -rf en .claude', () => {
    const r = runHook('rm -rf .claude');
    assert.equal(r.exitCode, 2);
  });
});
