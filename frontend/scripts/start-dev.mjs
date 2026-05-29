import { openSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const nodeRoot = resolve(root, '.tools/node-v24.16.0-win-x64');
const nodeExe = resolve(nodeRoot, 'node.exe');
const viteCli = resolve(root, 'node_modules/vite/bin/vite.js');
const env = { ...process.env };

for (const key of Object.keys(env)) {
  if (key.toLowerCase() === 'path') {
    delete env[key];
  }
}

env.Path = `${nodeRoot};${resolve(root, 'node_modules/.bin')};${process.env.Path || process.env.PATH || ''}`;

const out = openSync(resolve(root, 'dev-server.log'), 'a');
const err = openSync(resolve(root, 'dev-server.err.log'), 'a');

const child = spawn(nodeExe, [viteCli, '--host', '127.0.0.1', '--port', '5173'], {
  cwd: root,
  detached: true,
  env,
  stdio: ['ignore', out, err],
  windowsHide: true,
});

child.unref();
console.log(child.pid);
