// Only fixed messages may reach public Actions logs; outputs can contain private data.
import { readFileSync } from 'node:fs';

const messages = {
  approved: 'SES production access is approved.',
  submitted: 'SES production access was requested; AWS review is pending.',
  pending: 'SES production access is already under review.',
  denied: 'SES production access was denied; review the existing case in the AWS console.',
  'review-granted': 'SES review was granted, but production sending is not yet enabled; check the AWS console.',
  'identity-unverified': 'SES production access was not requested: verify the sender identity and deploy again.',
};
try {
  const { bootstrapStatus } = JSON.parse(readFileSync('.sst/outputs.json', 'utf8'));
  if (!bootstrapStatus || !Object.hasOwn(messages, bootstrapStatus.ses) || !['created', 'existing'].includes(bootstrapStatus.admin)) {
    throw new Error('Invalid bootstrap status');
  }
  console.log('Database initialization completed; the administrator account is ready.');
  console.log(messages[bootstrapStatus.ses]);
} catch {
  console.error('Unable to read deployment initialization status. Inspect private deployment outputs.');
  process.exitCode = 1;
}
