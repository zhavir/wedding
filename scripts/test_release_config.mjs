import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { test } from 'node:test';

const baseline = {
  STAGE: 'production',
  WEDDING_GROOM_NAME: 'Example groom',
  WEDDING_GROOM_EMAIL: 'groom@example.com',
  WEDDING_BRIDE_NAME: 'Example bride',
  WEDDING_BRIDE_EMAIL: 'bride@example.com',
  AWS_ACCOUNT_ID: '123456789012',
  AWS_DEPLOY_ROLE_ARN: 'arn:aws:iam::123456789012:role/deploy',
  SITE_DOMAIN: 'EXAMPLE.COM',
  EMAIL_FROM: 'wedding@example.com',
  SES_IDENTITY_ARN: '',
  RSVP_NOTIFICATION_EMAIL: '',
};
function validate(overrides) {
  return spawnSync(process.execPath, ['scripts/validate_release_config.mjs'], {
    env: { ...process.env, ...baseline, ...overrides }, encoding: 'utf8',
  });
}
test('accepts uppercase domain and an empty optional SES override from GitHub', () => {
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
test('requires managed-domain sender or a same-account Frankfurt SES override', () => {
  assert.equal(validate({ EMAIL_FROM: 'sender@other.com' }).status, 1);
  assert.equal(validate({ EMAIL_FROM: 'sender@other.com', SES_IDENTITY_ARN: 'arn:aws:ses:eu-central-1:123456789012:identity/other.com' }).status, 0);
  for (const SES_IDENTITY_ARN of ['arn:aws:ses:us-east-1:123456789012:identity/other.com', 'arn:aws:ses:eu-central-1:999999999999:identity/other.com']) {
    assert.equal(validate({ SES_IDENTITY_ARN }).status, 1);
  }
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
