/**
 * Used by bootstrap-on-pull.cmd: prints two tokens "KIMI DEEP" as 0 or 1
 * (1 = key present and not YOUR_* placeholder).
 */
import fs from 'fs';
import path from 'path';

const root = process.argv[2] || process.cwd();
const configPath = path.join(root, '.cursor', 'ai-model-shim', 'config.json');

function ok(v) {
  const s = String(v ?? '');
  return s.length > 0 && !s.startsWith('YOUR_') ? 1 : 0;
}

try {
  const raw = fs.readFileSync(configPath, 'utf8');
  const j = JSON.parse(raw);
  const kimi = ok(j?.keys?.kimi);
  const deep = ok(j?.keys?.deepseek);
  process.stdout.write(`${kimi} ${deep}\n`);
} catch {
  process.stdout.write('0 0\n');
}
