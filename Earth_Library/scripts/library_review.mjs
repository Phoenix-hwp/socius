import { readFileSync, statSync, appendFileSync } from "node:fs";
import { join } from "node:path";

const root = process.env.CURSOR_PROJECT_DIR || process.cwd();
const lib = join(root, "Earth_Library");
const cardsPath = join(lib, "cards.jsonl");
const relPath = join(lib, "relations.jsonl");
const queuePath = join(lib, "Review_Queue.md");

const SIMILARITY_THRESHOLD = 0.6;
const TAG_SIMILARITY_THRESHOLD = 0.5;

function parseTags(raw) {
  if (typeof raw === "string") return raw.replace(/，/g, ",").split(",").map((s) => s.trim()).filter(Boolean);
  if (Array.isArray(raw)) return raw.flatMap((item) => parseTags(item));
  return [];
}

function tokenize(text) {
  return new Set(text.split(/[,，\s]+/).map((x) => x.trim().toLowerCase()).filter(Boolean));
}

function loadCards() {
  if (!statSync(cardsPath, { throwIfNoEntry: false })?.isFile()) {
    process.stdout.write(JSON.stringify({ ok: false, error: "cards.jsonl 不存在" }));
    process.exit(1);
  }
  return readFileSync(cardsPath, "utf8").split("\n").filter((l) => l.trim()).map((l) => {
    try { return JSON.parse(l); } catch { return null; }
  }).filter(Boolean);
}

const date = new Date().toISOString().slice(0, 10);
const cards = loadCards();

if (cards.length < 2) {
  process.stdout.write(JSON.stringify({ ok: true, pairs: 0, tag_pairs: 0, message: "卡片数不足，跳过对比" }));
  process.exit(0);
}

let kwPairs = 0;
let tagPairs = 0;

for (let i = 0; i < cards.length; i++) {
  const a = cards[i];
  const ka = tokenize((a.body_md || "") + " " + (a.title || ""));
  const taga = new Set(parseTags(a.tags || []).map((t) => t.toLowerCase()));
  const idA = a.id || a.path || "";

  for (let j = i + 1; j < cards.length; j++) {
    const b = cards[j];
    const kb = tokenize((b.body_md || "") + " " + (b.title || ""));
    const tagb = new Set(parseTags(b.tags || []).map((t) => t.toLowerCase()));
    const idB = b.id || b.path || "";

    if (ka.size > 0 && kb.size > 0) {
      const inter = [...ka].filter((x) => kb.has(x)).length;
      const union = new Set([...ka, ...kb]).size;
      const score = union ? inter / union : 0;

      if (score >= SIMILARITY_THRESHOLD) {
        kwPairs++;
        appendFileSync(queuePath,
          `\n| ${date} | \`${idA}\` | 疑似重复 | 与 \`${idB}\` 关键词重合度 ${score.toFixed(2)} | 合并或区分边界 | 待处理 |`,
          "utf8");
        appendFileSync(relPath,
          JSON.stringify({ d: date, s: idA, t: idB, r: "疑似重复", x: `关键词重合度 ${score.toFixed(2)}` }) + "\n",
          "utf8");
      }
    }

    if (taga.size > 0 && tagb.size > 0) {
      const tInter = [...taga].filter((x) => tagb.has(x)).length;
      const tUnion = new Set([...taga, ...tagb]).size;
      const tScore = tUnion ? tInter / tUnion : 0;

      if (tScore >= TAG_SIMILARITY_THRESHOLD) {
        tagPairs++;
        appendFileSync(queuePath,
          `\n| ${date} | \`${idA}\` | 标签近邻 | 与 \`${idB}\` 标签重合度 ${tScore.toFixed(2)} | 建议检查主题聚合 | 待处理 |`,
          "utf8");
        appendFileSync(relPath,
          JSON.stringify({ d: date, s: idA, t: idB, r: "标签近邻", x: `标签重合度 ${tScore.toFixed(2)}` }) + "\n",
          "utf8");
      }
    }
  }
}

process.stdout.write(JSON.stringify({ ok: true, pairs: kwPairs, tag_pairs: tagPairs }));
