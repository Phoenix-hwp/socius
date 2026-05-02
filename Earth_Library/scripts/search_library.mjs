import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const root = process.cwd();
const cards = join(root, "Earth_Library", "Knowledge_Cards");
const args = Object.fromEntries(
  process.argv.slice(2).map((v, i, a) => (v.startsWith("--") ? [v.slice(2), a[i + 1]] : null)).filter(Boolean)
);
const q = String(args.q || "").toLowerCase().trim();
if (!q) {
  process.stdout.write("No query.\n");
  process.exit(0);
}
const hits = [];
for (const name of readdirSync(cards)) {
  const p = join(cards, name);
  if (!statSync(p).isFile() || !name.endsWith(".md")) continue;
  const text = readFileSync(p, "utf8").toLowerCase();
  if (text.includes(q)) hits.push(relative(root, p).replace(/\\/g, "/"));
}
process.stdout.write(hits.length ? `${hits.join("\n")}\n` : "No matches.\n");
