import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { test } from 'node:test';

const baseline = {
  STAGE: 'production',
  ADMIN_USERNAME: 'wedding-admin',
  WEDDING_GROOM_NAME: 'Example groom',
  WEDDING_GROOM_EMAIL: 'groom@example.com',
  WEDDING_BRIDE_NAME: 'Example bride',
  WEDDING_BRIDE_EMAIL: 'bride@example.com',
  AWS_ACCOUNT_ID: '123456789012',
  AWS_DEPLOY_ROLE_ARN: 'arn:aws:iam::123456789012:role/deploy',
  SITE_DOMAIN: 'EXAMPLE.COM',
  EMAIL_FROM: 'wedding@example.com',
  RSVP_NOTIFICATION_EMAIL: '',
};
function validate(overrides) {
  return spawnSync(process.execPath, ['scripts/validate_release_config.mjs'], {
    env: { ...process.env, ...baseline, ...overrides }, encoding: 'utf8',
  });
}
test('accepts uppercase site domain', () => {
  assert.equal(validate({}).status, 0);
});
test('DNS bootstrap does not require a sender', () => {
  assert.equal(validate({ STAGE: 'production-dns', EMAIL_FROM: '' }).status, 0);
});
test('rejects malformed domains and missing application sender', () => {
  for (const SITE_DOMAIN of ['', 'https://example.com', 'example.com/path', ' example.com', '-bad.com', 'a..com']) {
    assert.equal(validate({ SITE_DOMAIN }).status, 1);
  }
  assert.equal(validate({ EMAIL_FROM: '' }).status, 1);
});
test('accepts a Resend sender on a separate verified domain', () => {
  assert.equal(validate({ EMAIL_FROM: 'sender@mail.other.com' }).status, 0);
});
test('rejects cross-account deployment and unintended stages without printing values', () => {
  assert.equal(validate({ AWS_DEPLOY_ROLE_ARN: 'arn:aws:iam::999999999999:role/deploy' }).status, 1);
  const result = validate({ STAGE: 'sensitive-invalid-value' });
  assert.equal(result.status, 1);
  assert.ok(!`${result.stdout}${result.stderr}`.includes('sensitive-invalid-value'));
});

test('requires private host seed configuration without echoing it', () => {
  for (const key of ['WEDDING_GROOM_NAME', 'WEDDING_GROOM_EMAIL', 'WEDDING_BRIDE_NAME', 'WEDDING_BRIDE_EMAIL']) {
    assert.equal(validate({ [key]: '' }).status, 1);
    assert.equal(validate({ STAGE: 'production-dns', [key]: '' }).status, 0);
  }
  const result = validate({ WEDDING_GROOM_EMAIL: 'private-invalid-address' });
  assert.equal(result.status, 1);
  assert.ok(!`${result.stdout}${result.stderr}`.includes('private-invalid-address'));
});

test('requires admin username only for application deployment without leaking values', () => {
  for (const ADMIN_USERNAME of ['', 'ab', 'private invalid username', 'a'.repeat(101)]) {
    const result = validate({ ADMIN_USERNAME });
    assert.equal(result.status, 1);
    if (ADMIN_USERNAME) assert.ok(!`${result.stdout}${result.stderr}`.includes(ADMIN_USERNAME));
    assert.equal(validate({ STAGE: 'production-dns', ADMIN_USERNAME }).status, 0);
  }
});
