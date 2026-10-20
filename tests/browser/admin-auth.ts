import { readFileSync } from 'node:fs';
import { createHmac } from 'node:crypto';
import { test } from '@playwright/test';

let nextAccount = 0;
export function adminCredentials(): { username: string; password: string; secret: string } {
  const data = JSON.parse(readFileSync(process.env.ADMIN_TEST_CREDENTIALS!, 'utf8'));
  const offset = test.info().project.name === 'mobile' ? 32 : 0;
  const account = data.accounts[offset + nextAccount++];
  if (!account) throw new Error('No isolated administrator fixture remains');
  return account;
}

export function authenticatorCode(secret: string): string {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = '';
  for (const character of secret) bits += alphabet.indexOf(character).toString(2).padStart(5, '0');
  const key = Buffer.from(Array.from({ length: Math.floor(bits.length / 8) }, (_, index) => parseInt(bits.slice(index * 8, index * 8 + 8), 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(Math.floor(Date.now() / 30000)));
  const digest = createHmac('sha1', key).update(counter).digest();
  const offset = digest[digest.length - 1] & 15;
  return String((digest.readUInt32BE(offset) & 0x7fffffff) % 1000000).padStart(6, '0');
}
