import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { test } from 'node:test';

test('private commands suppress stdout and stderr, preserving failure', () => {
  for (const code of [0, 7]) {
    const result = spawnSync(process.execPath, ['scripts/private-command.mjs', process.execPath, '-e',
      `console.log('private-address'); console.error('private-arn'); process.exit(${code});`], { encoding: 'utf8' });
    assert.equal(result.status, code);
    assert.ok(!`${result.stdout}${result.stderr}`.includes('private-address'));
    assert.ok(!`${result.stdout}${result.stderr}`.includes('private-arn'));
  }
});

test('private command startup failure does not leak the command', () => {
  const result = spawnSync(process.execPath, ['scripts/private-command.mjs', '/missing/private-command'], { encoding: 'utf8' });
  assert.equal(result.status, 1);
  assert.ok(!`${result.stdout}${result.stderr}`.includes('/missing/private-command'));
});

test('generated output masks traverse objects and lists and escape workflow commands', () => {
  const cwd = mkdtempSync(join(process.cwd(), '.release-privacy-'));
  try {
    mkdirSync(join(cwd, '.sst'));
    writeFileSync(join(cwd, '.sst/outputs.json'), JSON.stringify({ website: 'https://example.com', nested: { ns: ['ns.example.com', 'line%\r\nvalue'] } }));
    const result = spawnSync(process.execPath, [resolve('scripts/mask-deployment-outputs.mjs')], { cwd, encoding: 'utf8' });
    assert.ifError(result.error);
    assert.equal(result.status, 0);
    assert.equal(result.stdout, '::add-mask::https://example.com\n::add-mask::ns.example.com\n::add-mask::line%25%0D%0Avalue\n');
    writeFileSync(join(cwd, '.sst/outputs.json'), 'invalid-private-data');
    const failed = spawnSync(process.execPath, [resolve('scripts/mask-deployment-outputs.mjs')], { cwd, encoding: 'utf8' });
    assert.equal(failed.status, 1);
    assert.ok(!`${failed.stdout}${failed.stderr}`.includes('invalid-private-data'));
  } finally {
    rmSync(cwd, { recursive: true, force: true });
  }
});
