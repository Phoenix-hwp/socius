import { readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const root = process.env.CURSOR_PROJECT_DIR || process.cwd();
const cardsPath = join(root, "Earth_Library", "cards.jsonl");
const relPath = join(root, "Earth_Library", "relations.jsonl");

const args = Object.fromEntries(
  process.argv.slice(2).map((v, i, a) => (v.startsWith("--") ? [v.slice(2), a[i + 1]] : null)).filter(Boolean)
);

const cardId = String(args.card_id || "").trim();
if (!cardId) {
  process.stdout.write(JSON.stringify({ ok: false, error: "missing --card_id" }));
  process.exit(1);
}

const relTypes = new Set(String(args.relation_types || "标签相交,关键词相交").split(",").map((s) => s.trim()));
const maxResults = parseInt(args.max_results || "5", 10);

function parseTags(raw) {
  if (typeof raw === "string") return raw.replace(/，/g, ",").split(",").map((s) => s.trim()).filter(Boolean);
  if (Array.isArray(raw)) return raw.flatMap((item) => parseTags(item));
  return [];
}

// Load cards map
const cardMap = {};
if (statSync(cardsPath, { throwIfNoEntry: false })?.isFile()) {
  for (const line of readFileSync(cardsPath, "utf8").split("\n")) {
    if (!line.trim()) continue;
    try {
      const c = JSON.parse(line);
      if (c.id) cardMap[c.id] = c;
    } catch {}
  }
}

// Load relations
const relatedIds = new Set();
if (statSync(relPath, { throwIfNoEntry: false })?.isFile()) {
  for (const line of readFileSync(relPath, "utf8").split("\n")) {
    if (!line.trim()) continue;
    try {
      const rel = JSON.parse(line);
      if (!relTypes.has(rel.r)) continue;
      if (rel.s === cardId && rel.t) relatedIds.add(rel.t);
      else if (rel.t === cardId && rel.s) relatedIds.add(rel.s);
    } catch {}
  }
}

const hits = [...relatedIds].slice(0, maxResults)
  .map((rid) => {
    const c = cardMap[rid];
    if (!c) return null;
    return {
      id: rid,
      title: c.title || "",
      type: c.type || "",
      confidence: c.confidence || "",
      domain: c.domain || "",
      tags: parseTags(c.tags || []),
    };
  })
  .filter(Boolean);

process.stdout.write(JSON.stringify({ ok: true, card_id: cardId, related: hits, total: hits.length }));
