// Only fixed messages may reach public Actions logs; outputs can contain private data.
import { readFileSync } from 'node:fs';

try {
  const { bootstrapStatus } = JSON.parse(readFileSync('.sst/outputs.json', 'utf8'));
  if (!bootstrapStatus || !['created', 'existing'].includes(bootstrapStatus.admin)) {
    throw new Error('Invalid bootstrap status');
  }
  console.log('Database initialization completed; the administrator account is ready.');
} catch {
  console.error('Unable to read deployment initialization status. Inspect private deployment outputs.');
  process.exitCode = 1;
}
