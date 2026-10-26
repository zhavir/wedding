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
async function dns(overrides = {}, zones = [existingZone], lookupError = null, existingRecords = [], recordsError = null) {
  const zoneCalls = [];
  const records = new Map();
  const recordOptions = new Map();
  const values = {
    ResendDkim: 'p=' + 'A'.repeat(400),
    ResendRsend: 'rsend.example.net',
    ResendSend: 'send.example.net.',
    ImprovMxPrimaryMx: '10 mx1.improvmx.com',
    ImprovMxSecondaryMx: '20 mx2.improvmx.com',
    ImprovMxSpf: 'v=spf1 include:spf.improvmx.com ~all',
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
    $output: (value) => new SecretOutput(value),
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
        getRecords: async ({ zoneId }) => {
          assert.ok(zones.some((zone) => zone.zoneId === zoneId));
          if (recordsError) throw recordsError;
          return { resourceRecordSets: existingRecords };
        },
        Record: class { constructor(name, args, options) {
          records.set(name, args);
          recordOptions.set(name, options);
        } },
      },
      ses: {
        DomainIdentity: class { domain = 'example.com'; verificationToken = 'legacy'; arn = 'legacy'; },
        DomainDkim: class { dkimTokens = ['one', 'two', 'three']; },
      },
    },
  };
  runInNewContext(source, sandbox);
  const outputs = await sandbox.exports.default.run();
  return { records, outputs, SecretOutput, zoneCalls, recordOptions };
}

test('DNS stage creates outbound Resend and inbound ImprovMX records and splits long DKIM values', async () => {
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
  assert.deepEqual(Array.from(mx.records, record => record.value), [
    '10 mx1.improvmx.com', '20 mx2.improvmx.com',
  ]);
  assert.equal(records.get('ImprovMxSpfRecord').records[0].value, 'v=spf1 include:spf.improvmx.com ~all');
  assert.ok(!JSON.stringify(outputs).includes('Resend'));
  assert.ok(records.has('EmailVerification') && records.has('EmailDmarc'));
});

test('short DKIM values remain unchanged', async () => {
  const { records } = await dns({ ResendDkim: 'p=example' });
  assert.equal(records.get('ResendDkimRecord').records[0].value, 'p=example');
});

test('missing or malformed DNS values fail without echoing their contents', async () => {
  for (const [index, overrides] of [
    { ResendDkim: undefined }, { ResendDkim: '' },
    { ResendDkim: 'private-value\n' }, { ResendDkim: '"private-value"' },
    { ResendRsend: 'https://private-value.example' }, { ResendSend: '' },
    { ImprovMxPrimaryMx: undefined }, { ImprovMxPrimaryMx: '' },
    { ImprovMxPrimaryMx: 'receive.private-value.example' },
    { ImprovMxPrimaryMx: '65536 receive.private-value.example' },
    { ImprovMxPrimaryMx: '10 https://private-value.example' },
    { ImprovMxSecondaryMx: '10 receive.private-value.example\n' },
    { ImprovMxSecondaryMx: undefined }, { ImprovMxSecondaryMx: '' },
    { ImprovMxSpf: undefined }, { ImprovMxSpf: '' },
    { ImprovMxSpf: 'v=spf1 include:private-value.example\n ~all' },
    { ImprovMxSpf: 'v=spf1 include:private-value.example' },
  ].entries()) {
    await assert.rejects(dns(overrides), (error) => {
      assert.ok(!error.message.includes('private-value'));
      return true;
    }, `Invalid DNS fixture ${index} must be rejected`);
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

test('adopts existing SES and DMARC records without overwriting their values', async () => {
  const existingRecords = [
    { name: '_amazonses.example.com.', type: 'TXT' },
    ...['one', 'two', 'three'].map((token) => ({ name: `${token}._domainkey.example.com.`, type: 'CNAME' })),
    { name: '_DMARC.EXAMPLE.COM.', type: 'TXT' },
    { name: 'www.example.com.', type: 'A' },
  ];
  const { records, recordOptions } = await dns({}, [existingZone], null, existingRecords);
  for (const id of ['EmailVerification', 'EmailDkim0', 'EmailDkim1', 'EmailDkim2', 'EmailDmarc']) {
    const args = records.get(id);
    assert.equal(recordOptions.get(id).import, `Z123_${args.name}_${args.type}`);
    assert.equal(args.allowOverwrite, undefined);
  }
  assert.equal(recordOptions.get('ResendDkimRecord').import, undefined);
  assert.ok(![...records.values()].some((args) => args.name === 'www.example.com'));
});

test('adopts Resend records after a partially successful deployment', async () => {
  const { recordOptions } = await dns({}, [existingZone], null, [
    { name: 'resend._domainkey.example.com.', type: 'TXT' },
    { name: 'example.com.', type: 'MX' },
  ]);
  assert.equal(recordOptions.get('ResendDkimRecord').import, 'Z123_resend._domainkey.example.com_TXT');
  assert.equal(recordOptions.get('ResendReceivingMxRecord').import, 'Z123_example.com_MX');
});

test('SPF updates preserve unrelated apex TXT records', async () => {
  const { records, recordOptions } = await dns({}, [existingZone], null, [{
    name: 'example.com.', type: 'TXT', resourceRecords: [
      { value: '"verification=keep-me"' },
      { value: '"v=spf1 include:old.example.net ~all"' },
    ],
  }]);
  const spf = records.get('ImprovMxSpfRecord');
  assert.equal(recordOptions.get('ImprovMxSpfRecord').import, 'Z123_example.com_TXT');
  assert.equal(spf.records[0], 'verification=keep-me');
  assert.equal(spf.records[1].value, 'v=spf1 include:spf.improvmx.com ~all');
  assert.equal(spf.records.length, 2);
});

test('record discovery errors and routed records fail without creating replacements', async () => {
  const error = new Error('Access denied listing records');
  await assert.rejects(dns({}, [existingZone], null, [], error), (actual) => actual === error);
  await assert.rejects(dns({}, [existingZone], null, [
    { name: '_dmarc.example.com.', type: 'TXT', setIdentifier: 'weighted' },
  ]), /Cannot adopt routed DNS record/);
});
