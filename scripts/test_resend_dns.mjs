import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { runInNewContext } from 'node:vm';
import ts from 'typescript';

const source = ts.transpileModule(readFileSync('sst.config.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;

// Evaluate the DNS branch without AWS access or real secret values.
async function dns(overrides = {}) {
  const records = new Map();
  const values = {
    ResendDkim: 'p=' + 'A'.repeat(400),
    ResendRsend: 'rsend.example.net',
    ResendSend: 'send.example.net.',
    ...overrides,
  };
  class SecretOutput {
    constructor(value) { this.value = value; }
    apply(fn) { return new SecretOutput(fn(this.value)); }
  }
  const sandbox = {
    exports: {},
    process: { env: { SITE_DOMAIN: 'EXAMPLE.COM' } },
    $config: (config) => config,
    $app: { stage: 'production-dns' },
    $interpolate: (strings, ...args) => String.raw({ raw: strings }, ...args),
    sst: { Secret: class {
      constructor(name) {
        if (values[name] === undefined) throw new Error('Missing secret: ' + name);
        this.value = new SecretOutput(values[name]);
      }
    } },
    aws: {
      route53: {
        Zone: class { zoneId = 'zone-id'; nameServers = ['ns.example.net']; },
        Record: class { constructor(name, args) { records.set(name, args); } },
      },
      ses: {
        DomainIdentity: class { domain = 'example.com'; verificationToken = 'legacy'; arn = 'legacy'; },
        DomainDkim: class { dkimTokens = ['one', 'two', 'three']; },
      },
    },
  };
  runInNewContext(source, sandbox);
  const outputs = await sandbox.exports.default.run();
  return { records, outputs, SecretOutput };
}

test('DNS stage creates Resend records from secrets and splits long DKIM values', async () => {
  const { records, outputs, SecretOutput } = await dns();
  for (const [id, name, type] of [
    ['ResendDkimRecord', 'resend._domainkey', 'TXT'],
    ['ResendRsendRecord', 'rsend', 'CNAME'],
    ['ResendSendRecord', 'send', 'CNAME'],
  ]) {
    const record = records.get(id);
    assert.equal(record.zoneId, 'zone-id');
    assert.equal(record.name, name + '.example.com');
    assert.equal(record.type, type);
    assert.equal(record.ttl, 300);
    assert.ok(record.records[0] instanceof SecretOutput);
  }
  const chunks = records.get('ResendDkimRecord').records[0].value.split('""');
  assert.deepEqual(chunks.map((chunk) => chunk.length), [255, 147]);
  assert.equal(chunks.join(''), 'p=' + 'A'.repeat(400));
  assert.equal(records.get('ResendRsendRecord').records[0].value, 'rsend.example.net');
  assert.equal(records.get('ResendSendRecord').records[0].value, 'send.example.net.');
  assert.ok(!JSON.stringify(outputs).includes('Resend'));
  assert.ok(records.has('EmailVerification') && records.has('EmailDmarc'));
});

test('short DKIM values remain unchanged', async () => {
  const { records } = await dns({ ResendDkim: 'p=example' });
  assert.equal(records.get('ResendDkimRecord').records[0].value, 'p=example');
});

test('missing or malformed DNS values fail without echoing their contents', async () => {
  for (const overrides of [
    { ResendDkim: undefined }, { ResendDkim: '' },
    { ResendDkim: 'private-value\n' }, { ResendDkim: '"private-value"' },
    { ResendRsend: 'https://private-value.example' }, { ResendSend: '' },
  ]) {
    await assert.rejects(dns(overrides), (error) => {
      assert.ok(!error.message.includes('private-value'));
      return true;
    });
  }
});
