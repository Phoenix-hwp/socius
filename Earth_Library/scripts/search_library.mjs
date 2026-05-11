import { readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const root = process.env.CURSOR_PROJECT_DIR || process.cwd();
const cardsPath = join(root, "Earth_Library", "cards.jsonl");
const args = Object.fromEntries(
  process.argv.slice(2).map((v, i, a) => (v.startsWith("--") ? [v.slice(2), a[i + 1]] : null)).filter(Boolean)
);

const q = String(args.q || "").toLowerCase().trim();
if (!q) {
  process.stdout.write(JSON.stringify({ ok: false, error: "missing --q" }));
  process.exit(1);
}

const queries = q.split(/\s+/).filter(Boolean);
const tagsFilterRaw = (args.tag ? [args.tag].flat() : []);
const tagsFilter = new Set(tagsFilterRaw.map((t) => t.toLowerCase()));
const confOrder = { "高": 3, "中": 2, "低": 1 };
const confMin = confOrder[args.confidence_threshold] || 0;
const maxResults = parseInt(args.max_results || "10", 10);

function parseTags(raw) {
  if (typeof raw === "string") return raw.replace(/，/g, ",").split(",").map((s) => s.trim()).filter(Boolean);
  if (Array.isArray(raw)) return raw.flatMap((item) => parseTags(item));
  return [];
}

function snippet(text, query, window = 60) {
  const pos = text.toLowerCase().indexOf(query.toLowerCase());
  if (pos === -1) return text.slice(0, window * 2) + (text.length > window * 2 ? "…" : "");
  const start = Math.max(0, pos - Math.floor(window / 2));
  const end = Math.min(text.length, pos + query.length + Math.floor(window / 2));
  let s = text.slice(start, end);
  if (start > 0) s = "…" + s;
  if (end < text.length) s += "…";
  return s;
}

if (!statSync(cardsPath, { throwIfNoEntry: false })?.isFile()) {
  process.stdout.write(JSON.stringify({ ok: false, error: "cards.jsonl 不存在" }));
  process.exit(1);
}

const lines = readFileSync(cardsPath, "utf8").split("\n").filter((l) => l.trim());
const hits = [];

for (const line of lines) {
  let card;
  try { card = JSON.parse(line); } catch { continue; }

  const cardConf = card.confidence || "中";
  if ((confOrder[cardConf] || 0) < confMin) continue;

  const cardTags = parseTags(card.tags || []);
  const cardTagsLower = new Set(cardTags.map((t) => t.toLowerCase()));
  if (tagsFilter.size > 0 && ![...tagsFilter].some((t) => cardTagsLower.has(t))) continue;

  const title = (card.title || "").toLowerCase();
  const body = (card.body_md || "").toLowerCase();
  const kwList = parseTags(card.keywords || []);
  const searchText = [title, body, ...kwList, ...cardTags].join(" ").toLowerCase();

  const matchCount = queries.filter((q) => searchText.includes(q)).length;
  if (matchCount === 0) continue;

  const titleMatch = queries.filter((q) => title.includes(q)).length;
  const score = matchCount + titleMatch * 2;

  const hitTags = tagsFilter.size > 0
    ? cardTags.filter((t) => tagsFilter.has(t.toLowerCase()))
    : cardTags;

  hits.push({
    id: card.id || "",
    title: card.title || "",
    type: card.type || "",
    confidence: cardConf,
    domain: card.domain || "",
    tags: hitTags,
    score,
    snippet: snippet(card.body_md || "", queries[0]),
    source: card.source || "",
  });
}

hits.sort((a, b) => b.score - a.score || (confOrder[b.confidence] || 0) - (confOrder[a.confidence] || 0));
const result = hits.slice(0, maxResults);

process.stdout.write(JSON.stringify({ ok: true, q: args.q, hits: result, total: result.length }));
