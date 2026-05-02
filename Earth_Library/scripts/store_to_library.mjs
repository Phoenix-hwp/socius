import { mkdirSync, readFileSync, readdirSync, statSync, appendFileSync, writeFileSync } from "node:fs";
import { join, relative } from "node:path";

const root = process.cwd();
const libRoot = join(root, "Earth_Library");
const cardsDir = join(libRoot, "Knowledge_Cards");
const indexPath = join(libRoot, "Library_Index.md");
const relPath = join(libRoot, "Relations", "Relations_Index.md");
const queuePath = join(libRoot, "Review_Queue.md");
const cfgPath = join(libRoot, "System", "ingest_config.json");
const tagPath = join(libRoot, "System", "tag_dictionary.json");

const args = Object.fromEntries(
  process.argv.slice(2).map((v, i, a) => (v.startsWith("--") ? [v.slice(2), a[i + 1]] : null)).filter(Boolean)
);
const title = args.title || "untitled";
const content = args.content || "";
const type = args.type || "知识记录";
const source = args.source || "对话沉淀";
const source_mode = args.source_mode || "conversation";
const source_url = args.source_url || "";
const source_path = args.source_path || "";
const confidence = args.confidence || "中";
const keywords = args.keywords || "";
const cfg = JSON.parse(readFileSync(cfgPath, "utf8"));
const tagCfg = JSON.parse(readFileSync(tagPath, "utf8"));
if (!cfg.source_modes.includes(source_mode)) {
  throw new Error(`unsupported source_mode: ${source_mode}`);
}

function slugify(text) {
  return text.trim().replace(/[^\w\u4e00-\u9fff-]+/g, "-").replace(/-{2,}/g, "-").replace(/^-|-$/g, "") || "untitled";
}
function readKeywords(text) {
  return new Set(text.split(/[,，\s]+/).map((x) => x.trim().toLowerCase()).filter(Boolean));
}
function readTagsFromCard(text) {
  const m = text.match(/^Tags:\s*(.+)$/m);
  if (!m) return new Set();
  return new Set(m[1].split(/[,，\s]+/).map((x) => x.trim().toLowerCase()).filter(Boolean));
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
const cardName = `${ts}_${slugify(title)}.md`;
const cardPath = join(cardsDir, cardName);
const cardRel = relative(root, cardPath).replace(/\\/g, "/");
const newKw = readKeywords(keywords);
const maxTags = Number(tagCfg.recommended_tag_count?.default || 5);
const tags = inferTags([title, content, type, source, source_url, source_mode, confidence, keywords].join(" "), maxTags);
const newTags = new Set(tags.map((t) => t.toLowerCase()));

mkdirSync(cardsDir, { recursive: true });
const related = [];
const tagRelated = [];
const conflicts = [];
for (const name of readdirSync(cardsDir)) {
  const p = join(cardsDir, name);
  if (!statSync(p).isFile() || !name.endsWith(".md")) continue;
  const text = readFileSync(p, "utf8");
  const existing = readKeywords(text);
  const existingTags = readTagsFromCard(text);
  if ([...newKw].some((k) => existing.has(k))) related.push(relative(root, p).replace(/\\/g, "/"));
  if ([...newTags].some((k) => existingTags.has(k))) tagRelated.push(relative(root, p).replace(/\\/g, "/"));
  if (text.includes("# Summary") && text.includes(title) && (content.includes("冲突") || content.includes("相反"))) {
    conflicts.push(relative(root, p).replace(/\\/g, "/"));
  }
}

const cardText = [
  "---",
  "Lifecycle: 阶段",
  `Title: ${title}`,
  `Type: ${type}`,
  `Source: ${source}`,
  `SourceMode: ${source_mode}`,
  `SourceURL: ${source_url}`,
  `SourcePath: ${source_path}`,
  `Confidence: ${confidence}`,
  `Created: ${date}`,
  `Keywords: ${keywords}`,
  `Tags: ${tags.join(",")}`,
  "---",
  "",
  "# Summary",
  title,
  "",
  "# Details",
  content,
  "",
  "# Related",
  ...(related.length ? related.map((p) => `- ${p}`) : ["- (none)"]),
  "",
].join("\n");
writeFileSync(cardPath, cardText, "utf8");

appendFileSync(indexPath, `\n| ${date} | ${title} | ${type} | ${source} | ${keywords} | \`${cardRel}\` |`, "utf8");
for (const target of related) {
  appendFileSync(relPath, `\n| ${date} | \`${cardRel}\` | \`${target}\` | 关键词相交 | 自动关联（共享关键词） |`, "utf8");
}
for (const target of tagRelated) {
  appendFileSync(relPath, `\n| ${date} | \`${cardRel}\` | \`${target}\` | 标签相交 | 自动关联（共享标签） |`, "utf8");
}
for (const target of conflicts) {
  appendFileSync(relPath, `\n| ${date} | \`${cardRel}\` | \`${target}\` | 冲突 | 新增内容包含冲突语义，请人工复核 |`, "utf8");
  appendFileSync(
    queuePath,
    `\n| ${date} | \`${cardRel}\` | 冲突待复核 | 与 \`${target}\` 存在冲突标记语义 | 人工确认口径并修订 | 待处理 |`,
    "utf8"
  );
}
if ((cfg.quality_rules?.low_confidence_values || []).includes(confidence)) {
  appendFileSync(
    queuePath,
    `\n| ${date} | \`${cardRel}\` | 低置信度 | 该条目标记为低置信度 | 补充来源与证据后复核 | 待处理 |`,
    "utf8"
  );
}

process.stdout.write(
  JSON.stringify({
    ok: true,
    card: cardRel,
    related_count: related.length,
    tag_related_count: tagRelated.length,
    conflict_count: conflicts.length,
    tag_max: maxTags,
  })
);
