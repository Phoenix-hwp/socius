import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const statePath = join(process.cwd(), "Earth_Library", "System", "library_switch.json");
const args = Object.fromEntries(
  process.argv.slice(2).map((v, i, a) => (v.startsWith("--") ? [v.slice(2), a[i + 1]] : null)).filter(Boolean)
);
const mode = args.mode;
const state = JSON.parse(readFileSync(statePath, "utf8"));
if (mode === "enable") state.enabled = true;
if (mode === "disable") state.enabled = false;
state.updated_at = new Date().toISOString();
writeFileSync(statePath, JSON.stringify(state, null, 2), "utf8");
process.stdout.write(JSON.stringify(state));
