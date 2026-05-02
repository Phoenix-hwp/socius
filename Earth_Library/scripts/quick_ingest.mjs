import { spawnSync } from "node:child_process";
import { join } from "node:path";

const root = process.cwd();
const store = join(root, "Earth_Library", "scripts", "store_to_library.mjs");
const args = Object.fromEntries(
  process.argv.slice(2).map((v, i, a) => (v.startsWith("--") ? [v.slice(2), a[i + 1]] : null)).filter(Boolean)
);

const text = String(args.text || "").trim();
if (!text) {
  process.stdout.write(JSON.stringify({ ok: false, error: "missing --text" }));
  process.exit(1);
}

const title = (args.title || text.slice(0, 24)).trim();
const type = args.type || "知识记录";
const source = args.source || "对话沉淀";
const confidence = args.confidence || "中";

const guessSourceMode = (t) => {
  const s = t.toLowerCase();
  if (s.includes("notion") || s.includes("notion.so")) return "notion_page";
  if (s.includes("http://") || s.includes("https://")) return "web_url";
  if (s.includes(".md") || s.includes("markdown")) return "markdown_file";
  return "conversation";
};
const extractUrl = (t) => {
  const m = t.match(/https?:\/\/\S+/);
  return m ? m[0] : "";
};
const buildKeywords = (t) => {
  const tokens = t.match(/[\u4e00-\u9fffA-Za-z0-9_]{2,}/g) || [];
  const seen = [];
  for (const k of tokens) if (!seen.includes(k)) seen.push(k);
  return seen.slice(0, 8).join(",");
};

const source_mode = guessSourceMode(text);
const source_url = extractUrl(text);
const keywords = buildKeywords(text);

const proc = spawnSync(
  "node",
  [
    store,
    "--title",
    title,
    "--content",
    text,
    "--type",
    type,
    "--source",
    source,
    "--source_mode",
    source_mode,
    "--source_url",
    source_url,
    "--confidence",
    confidence,
    "--keywords",
    keywords,
  ],
  { encoding: "utf8", cwd: root }
);

if ((proc.status ?? 1) !== 0) {
  process.stdout.write(JSON.stringify({ ok: false, error: (proc.stderr || "").trim() || "quick_ingest failed" }));
  process.exit(1);
}

const out = JSON.parse((proc.stdout || "{}").trim());
out.source_mode = source_mode;
out.source_url = source_url;
out.keywords = keywords;
process.stdout.write(JSON.stringify(out));
