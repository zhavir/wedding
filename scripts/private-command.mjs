// Never forward child output, including errors, to public Actions logs.
import { spawn } from 'node:child_process';

const [command, ...args] = process.argv.slice(2);
if (!command) throw new Error('A command is required.');
const child = spawn(command, args, { stdio: ['ignore', 'ignore', 'ignore'] });
child.on('error', () => {
  console.error('Private operation could not start. Inspect it from an authorized local terminal.');
  process.exitCode = 1;
});
child.on('exit', (code) => {
  if (code !== 0) {
    console.error('Private operation failed; output withheld. Inspect it from an authorized local terminal.');
  }
  process.exitCode = code ?? 1;
});
