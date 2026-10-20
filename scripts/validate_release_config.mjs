// Offline validation only: this script never authenticates or contacts AWS.
const required = [
  'STAGE', 'AWS_ACCOUNT_ID', 'AWS_DEPLOY_ROLE_ARN',
  'SITE_DOMAIN',
  ...(process.env.STAGE === 'production-dns' ? [] : ['EMAIL_FROM', 'WEDDING_GROOM_NAME', 'WEDDING_GROOM_EMAIL', 'WEDDING_BRIDE_NAME', 'WEDDING_BRIDE_EMAIL']),
];
const errors = [];
const values = Object.fromEntries(
  [...required, 'EMAIL_FROM', 'SES_IDENTITY_ARN', 'RSVP_NOTIFICATION_EMAIL'].map((key) => [key, process.env[key] ?? '']),
);
for (const key of required) {
  if (!values[key] || values[key] !== values[key].trim()) {
    errors.push(`${key} must be set without surrounding whitespace.`);
  }
}
if (!['production', 'production-dns'].includes(values.STAGE)) {
  errors.push('STAGE must be production or production-dns.');
}
if (!/^\d{12}$/.test(values.AWS_ACCOUNT_ID)) {
  errors.push('AWS_ACCOUNT_ID must contain exactly 12 digits.');
}
const role = /^arn:aws:iam::(\d{12}):role\/[\w+=,.@/-]+$/.exec(values.AWS_DEPLOY_ROLE_ARN);
if (!role || role[1] !== values.AWS_ACCOUNT_ID) {
  errors.push('AWS_DEPLOY_ROLE_ARN must be an IAM role in AWS_ACCOUNT_ID.');
}
const domain = values.SITE_DOMAIN.toLowerCase();
if (domain.length > 253 || !/^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/.test(domain)) {
  errors.push('SITE_DOMAIN must be a domain without a scheme, path or whitespace.');
}
const identity = /^arn:aws:ses:eu-central-1:(\d{12}):identity\/(.+)$/.exec(values.SES_IDENTITY_ARN);
if (values.SES_IDENTITY_ARN && (!identity || identity[1] !== values.AWS_ACCOUNT_ID)) {
  errors.push('SES_IDENTITY_ARN must be a Frankfurt SES identity in AWS_ACCOUNT_ID.');
}
// These settings are bare addresses; display names belong in the email template.
for (const key of ['EMAIL_FROM', 'RSVP_NOTIFICATION_EMAIL', ...(values.STAGE === 'production-dns' ? [] : ['WEDDING_GROOM_EMAIL', 'WEDDING_BRIDE_EMAIL'])]) {
  if (!values[key] && (key === 'RSVP_NOTIFICATION_EMAIL' || values.STAGE === 'production-dns')) continue;
  if (!/^[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+$/.test(values[key])) {
    errors.push(`${key} must be a bare email address.`);
  }
}
if (values.STAGE === 'production' && !values.SES_IDENTITY_ARN &&
    values.EMAIL_FROM.split('@')[1]?.toLowerCase() !== domain) {
  errors.push('EMAIL_FROM must belong to SITE_DOMAIN when using the SST-managed SES identity.');
}
if (errors.length) {
  // Report field names, never configuration values or credentials.
  for (const error of errors) console.error(error);
  process.exitCode = 1;
} else {
  console.log('Release configuration is valid locally. AWS permissions and SES verification still require live validation.');
}
