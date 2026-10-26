import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { runInNewContext } from 'node:vm';
import ts from 'typescript';

const source = ts.transpileModule(readFileSync('sst.config.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;

// Evaluate the DNS branch without AWS access or real secret values.
const existingZone = { zoneId: 'Z123', name: 'example.com.', privateZone: false, nameServers: ['ns.example.net'] };
async function dns(overrides = {}, zones = [existingZone], lookupError = null) {
  const zoneCalls = [];
  const records = new Map();
  const values = {
    ResendDkim: 'p=' + 'A'.repeat(400),
    ResendRsend: 'rsend.example.net',
    ResendSend: 'send.example.net.',
    ResendReceivingMx: '10 receive.example.net',
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
        Zone: class {
          constructor(name, args, options) {
            zoneCalls.push({ name, args, options });
            this.zoneId = options.import ?? 'ZNEW';
            this.nameServers = ['ns.example.net'];
          }
        },
        getZones: async () => {
          if (lookupError) throw lookupError;
          return { ids: zones.map((zone) => zone.zoneId) };
        },
        getZone: async (args) => {
          return zones.find((zone) => zone.zoneId === args.zoneId);
        },
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
  return { records, outputs, SecretOutput, zoneCalls };
}

test('DNS stage creates Resend records from secrets and splits long DKIM values', async () => {
  const { records, outputs, SecretOutput } = await dns();
  for (const [id, name, type] of [
    ['ResendDkimRecord', 'resend._domainkey', 'TXT'],
    ['ResendRsendRecord', 'rsend', 'CNAME'],
    ['ResendSendRecord', 'send', 'CNAME'],
  ]) {
    const record = records.get(id);
    assert.equal(record.zoneId, 'Z123');
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
  const mx = records.get('ResendReceivingMxRecord');
  assert.equal(mx.zoneId, 'Z123');
  assert.equal(mx.name, 'example.com');
  assert.equal(mx.type, 'MX');
  assert.equal(mx.ttl, 300);
  assert.ok(mx.records[0] instanceof SecretOutput);
  assert.equal(mx.records[0].value, '10 receive.example.net');
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
    { ResendReceivingMx: undefined }, { ResendReceivingMx: '' },
    { ResendReceivingMx: 'receive.private-value.example' },
    { ResendReceivingMx: '65536 receive.private-value.example' },
    { ResendReceivingMx: '10 https://private-value.example' },
    { ResendReceivingMx: '10 receive.private-value.example\n' },
  ]) {
    await assert.rejects(dns(overrides), (error) => {
      assert.ok(!error.message.includes('private-value'));
      return true;
    });
  }
});

test('creates a zone only when no public zone matches, then imports it on later runs', async () => {
  const first = await dns({}, []);
  assert.equal(first.zoneCalls[0].options.import, undefined);
  assert.equal(first.outputs.hostedZoneId, 'ZNEW');
  const second = await dns({}, [{ ...existingZone, zoneId: 'ZNEW' }]);
  assert.equal(second.zoneCalls[0].options.import, 'ZNEW');
  assert.equal(second.zoneCalls[0].options.protect, true);
  assert.equal(second.zoneCalls[0].options.retainOnDelete, true);
});

test('ignores private zones and zones for other domains', async () => {
  const { zoneCalls } = await dns({}, [
    { ...existingZone, privateZone: true },
    { ...existingZone, zoneId: 'ZOTHER', name: 'other.com.' },
  ]);
  assert.equal(zoneCalls[0].options.import, undefined);
});

test('rejects duplicate matches and propagates lookup failures', async () => {
  await assert.rejects(dns({}, [existingZone, { ...existingZone, zoneId: 'ZDUP' }]), /Multiple public hosted zones/);
  const error = new Error('Access denied');
  await assert.rejects(dns({}, [], error), (actual) => actual === error);
});

test('returns the existing zone and its nameservers', async () => {
  const { outputs, zoneCalls } = await dns();
  assert.equal(zoneCalls[0].options.import, 'Z123');
  assert.equal(outputs.hostedZoneId, 'Z123');
  assert.deepEqual(outputs.nameservers, ['ns.example.net']);
});
