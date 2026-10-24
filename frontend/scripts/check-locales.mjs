import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
const root = new URL('../src/lib/locales/', import.meta.url);
const read = (lang, section, name) =>
  JSON.parse(readFileSync(new URL(`${lang}/${section}/${name}`, root), 'utf8'));
function compare(en, it, path) {
  assert.equal(typeof en, typeof it, `Type mismatch: ${path}`);
  if (Array.isArray(en)) {
    assert.ok(Array.isArray(it), path);
    assert.equal(en.length, it.length, `Array length: ${path}`);
    en.forEach((value, i) => compare(value, it[i], `${path}[${i}]`));
  } else if (en && typeof en === 'object') {
    assert.deepEqual(Object.keys(en).sort(), Object.keys(it).sort(), `Keys: ${path}`);
    for (const key of Object.keys(en)) compare(en[key], it[key], `${path}.${key}`);
  } else if (typeof en === 'string') {
    assert.ok(en.trim() && it.trim() && it !== 'N/A', `Missing copy: ${path}`);
    assert.deepEqual(
      [...en.matchAll(/\{\w+\}/g)].map(String).sort(),
      [...it.matchAll(/\{\w+\}/g)].map(String).sort(),
      `Placeholders: ${path}`
    );
  }
}
for (const section of ['ui', 'content']) {
  const names = readdirSync(new URL(`en/${section}/`, root)).sort();
  assert.deepEqual(names, readdirSync(new URL(`it/${section}/`, root)).sort());
  const used = new Set();
  for (const name of names) {
    const en = read('en', section, name);
    compare(en, read('it', section, name), `${section}/${name}`);
    for (const key of Object.keys(en)) {
      assert.ok(!used.has(key), `Duplicate ${section} key: ${key}`);
      used.add(key);
    }
  }
}
assert.deepEqual(
  read('en', 'content', 'timeline.json').schedule.map((x) => x.time),
  read('it', 'content', 'timeline.json').schedule.map((x) => x.time)
);
console.log('Section translations, placeholders and confirmed timeline match.');
