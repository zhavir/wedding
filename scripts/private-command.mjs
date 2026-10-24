// Forward deployment output only when explicitly enabled for troubleshooting.
import { spawn } from 'node:child_process';

const [command, ...args] = process.argv.slice(2);
if (!command) throw new Error('A command is required.');
const debug = process.env.DEBUG_DEPLOY === '1';
const child = spawn(command, args, { stdio: ['ignore', debug ? 'inherit' : 'ignore', debug ? 'inherit' : 'ignore'] });
child.on('error', () => {
  console.error('Private operation could not start. Inspect it from an authorized local terminal.');
  process.exitCode = 1;
});
child.on('exit', (code) => {
  if (code !== 0) {
    console.error(debug ? 'Deployment operation failed; see output above.' : 'Private operation failed; output withheld. Inspect it from an authorized local terminal.');
  }
  process.exitCode = code ?? 1;
});
