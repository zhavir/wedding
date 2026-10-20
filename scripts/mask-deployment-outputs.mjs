import { readFileSync } from 'node:fs';

function mask(value) {
  if (typeof value === 'string' && value) {
    const escaped = value.replaceAll('%', '%25').replaceAll('\r', '%0D').replaceAll('\n', '%0A');
    console.log(`::add-mask::${escaped}`);
  } else if (value && typeof value === 'object') {
    Object.values(value).forEach(mask);
  }
}

try {
  mask(JSON.parse(readFileSync('.sst/outputs.json', 'utf8')));
} catch {
  console.error('Unable to register private deployment output masks.');
  process.exitCode = 1;
}
