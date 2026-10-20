import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const read = (name) =>
  JSON.parse(readFileSync(new URL(`../../content/${name}`, import.meta.url), 'utf8'));
const en = read('locales/en/ui.json');
const it = read('locales/it/ui.json');
assert.deepEqual(
  Object.keys(it).sort(),
  Object.keys(en).sort(),
  'Italian and English must have the same translation keys.'
);
for (const key of Object.keys(en)) {
  assert.equal(typeof it[key], 'string', `Translation must be text: ${key}`);
  assert.ok(it[key].trim(), `Missing Italian translation: ${key}`);
  assert.deepEqual(
    [...it[key].matchAll(/\{\w+\}/g)].map(([value]) => value).sort(),
    [...en[key].matchAll(/\{\w+\}/g)].map(([value]) => value).sort(),
    `Keep all placeholders in: ${key}`
  );
}
const wedding = read('locales/en/wedding.json');
const italian = read('locales/it/wedding.json');
assert.equal(
  italian.schedule.length,
  wedding.schedule.length,
  'Both languages must describe the same schedule.'
);
assert.deepEqual(
  italian.schedule.map(({ time }) => time),
  wedding.schedule.map(({ time }) => time),
  'Schedule times must agree.'
);
assert.equal(italian.faqs.length, wedding.faqs.length, 'Keep both FAQ lists up to date.');
console.log('English/Italian translation keys, placeholders and schedule match.');
