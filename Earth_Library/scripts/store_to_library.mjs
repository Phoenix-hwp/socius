import { mkdirSync, readFileSync, appendFileSync, writeFileSync, statSync } from "node:fs";
import { join } from "node:path";

const root = process.env.CURSOR_PROJECT_DIR || process.cwd();
const libRoot = join(root, "Earth_Library");
const cardsPath = join(libRoot, "cards.jsonl");
const indexPath = join(libRoot, "library_index.json");
const relPath = join(libRoot, "relations.jsonl");
const queuePath = join(libRoot, "Review_Queue.md");
const cfgPath = join(libRoot, "System", "ingest_config.json");
const tagPath = join(libRoot, "System", "tag_dictionary.json");

const args = Object.fromEntries(
  process.argv.slice(2).map((v, i, a) => (v.startsWith("--") ? [v.slice(2), a[i + 1]] : null)).filter(Boolean)
);
const title = args.title || "untitled";
let content = "";
if (args["content-file"]) {
  content = readFileSync(args["content-file"], "utf8");
} else if (args.content != null && args.content !== "") {
  content = String(args.content);
}
if (!content) {
  process.stdout.write(JSON.stringify({ ok: false, error: "必须提供 --content 或 --content-file" }));
  process.exit(1);
}
const type = args.type || "知识记录";
const source = args.source || "对话沉淀";
const sourceMode = args.source_mode || "conversation";
const sourceUrl = args.source_url || "";
const sourcePath = args.source_path || "";
const confidence = args.confidence || "中";
const keywords = args.keywords || "";
const notionPageId = args["notion-page-id"] || "";

const cfg = JSON.parse(readFileSync(cfgPath, "utf8"));
const tagCfg = JSON.parse(readFileSync(tagPath, "utf8"));
const maxTags = Number(tagCfg.recommended_tag_count?.default || 5);

function slugify(text) {
  return text.trim().replace(/[^\w\u4e00-\u9fff-]+/g, "-").replace(/-{2,}/g, "-").replace(/^-|-$/g, "") || "untitled";
}
function tokenize(text) {
  return new Set(text.split(/[,，\s]+/).map((x) => x.trim().toLowerCase()).filter(Boolean));
}
function parseTags(raw) {
  if (typeof raw === "string") return raw.replace(/，/g, ",").split(",").map((s) => s.trim()).filter(Boolean);
  if (Array.isArray(raw)) return raw.flatMap((item) => parseTags(item));
  return [];
}
function inferTags(payload, maxTags) {
  const text = payload.toLowerCase();
  const tags = [];
  for (const item of tagCfg.tags || []) {
    const name = item.name;
    const triggers = item.triggers || [];
    if (!name) continue;
    if (triggers.some((t) => text.includes(String(t).toLowerCase()))) tags.push(name);
  }
  return [...new Set(tags)].slice(0, maxTags);
}

const now = new Date();
const date = now.toISOString().slice(0, 10);
const ts = now.toISOString().replace(/[-:TZ.]/g, "").slice(0, 14);
const newId = `${ts}_${slugify(title)}`;
const tags = inferTags([title, content, type, source, sourceUrl, sourceMode, confidence, keywords].join(" "), maxTags);

mkdirSync(libRoot, { recursive: true });

// Build card object
const card = {
  id: newId,
  title,
  type,
  confidence,
  tags: tags.join(","),
  keywords,
  source,
  source_url: sourceUrl,
  source_mode: sourceMode,
  source_path: sourcePath,
  notion_page_id: notionPageId || "",
  lifecycle: "阶段",
  created: date,
  body_md: content,
};

// Append to cards.jsonl
appendFileSync(cardsPath, JSON.stringify(card) + "\n", "utf8");

// Update library_index.json
let index = { cards: [] };
try { index = JSON.parse(readFileSync(indexPath, "utf8")); } catch {}
index.cards.push({
  id: newId,
  title,
  type,
  source,
  date,
  keywords: keywords ? keywords.split(",").map((k) => k.trim()).filter(Boolean) : [],
  confidence,
});
writeFileSync(indexPath, JSON.stringify(index, null, 2), "utf8");

// Compute relations
const newKw = tokenize(content);
newKw.add(title.toLowerCase());
const newTagSet = new Set(tags.map((t) => t.toLowerCase()));

// Load existing cards for relation computation
let allCards = [];
if (statSync(cardsPath, { throwIfNoEntry: false })?.isFile()) {
  allCards = readFileSync(cardsPath, "utf8").split("\n").filter((l) => l.trim()).map((l) => {
    try { return JSON.parse(l); } catch { return null; }
  }).filter(Boolean);
}

let relatedCount = 0;
for (const existing of allCards) {
  const eid = existing.id || "";
  if (!eid || eid === newId) continue;

  const ekw = tokenize((existing.body_md || "") + " " + (existing.title || ""));
  const eTags = new Set(parseTags(existing.tags || []).map((t) => t.toLowerCase()));

  // 关键词相交
  if ([...newKw].some((k) => ekw.has(k))) {
    appendFileSync(relPath,
      JSON.stringify({ d: date, s: newId, t: eid, r: "关键词相交", x: "自动关联（共享关键词）" }) + "\n",
      "utf8");
    relatedCount++;
  }

  // 标签相交
  if ([...newTagSet].some((t) => eTags?.has(t))) {
    appendFileSync(relPath,
      JSON.stringify({ d: date, s: newId, t: eid, r: "标签相交", x: "自动关联（共享标签）" }) + "\n",
      "utf8");
    relatedCount++;
  }

  // 冲突检测
  if (
    (existing.body_md || "").includes("# Summary") &&
    (existing.body_md || "").includes(title) &&
    (content.includes("冲突") || content.includes("相反"))
  ) {
    appendFileSync(relPath,
      JSON.stringify({ d: date, s: newId, t: eid, r: "冲突", x: "新增内容包含冲突语义，请人工复核" }) + "\n",
      "utf8");
    appendFileSync(queuePath,
      `\n| ${date} | \`${newId}\` | 冲突待复核 | 与 \`${eid}\` 存在冲突标记语义 | 人工确认口径并修订 | 待处理 |`,
      "utf8");
  }
}

// Low confidence check
if ((cfg.quality_rules?.low_confidence_values || []).includes(confidence)) {
  appendFileSync(queuePath,
    `\n| ${date} | \`${newId}\` | 低置信度 | 该条目标记为低置信度 | 补充来源与证据后复核 | 待处理 |`,
    "utf8");
}

process.stdout.write(JSON.stringify({
  ok: true,
  action: "created",
  id: newId,
  related_count: relatedCount,
  tag_max: maxTags,
}));
