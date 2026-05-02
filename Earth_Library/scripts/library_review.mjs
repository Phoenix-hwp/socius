import { readdirSync, readFileSync, statSync, appendFileSync } from "node:fs";
import { join, relative } from "node:path";

const root = process.cwd();
const lib = join(root, "Earth_Library");
const cardsDir = join(lib, "Knowledge_Cards");
const queue = join(lib, "Review_Queue.md");
const rel = join(lib, "Relations", "Relations_Index.md");
const date = new Date().toISOString().slice(0, 10);

const files = readdirSync(cardsDir)
  .filter((n) => n.endsWith(".md") && n !== "README.md")
  .map((n) => join(cardsDir, n))
  .filter((p) => statSync(p).isFile());

const kws = (text) =>
  new Set(
    text
      .split(/[,，\s]+/)
      .map((x) => x.trim().toLowerCase())
      .filter(Boolean)
  );
const tags = (text) => {
  const m = text.match(/^Tags:\s*(.+)$/m);
  if (!m) return new Set();
  return new Set(
    m[1]
      .split(/[,，\s]+/)
      .map((x) => x.trim().toLowerCase())
      .filter(Boolean)
  );
};

let pairs = 0;
let tagPairs = 0;
for (let i = 0; i < files.length; i++) {
  const a = files[i];
  const ta = readFileSync(a, "utf8");
  const ka = kws(ta);
  const taga = tags(ta);
  for (let j = i + 1; j < files.length; j++) {
    const b = files[j];
    const tb = readFileSync(b, "utf8");
    const kb = kws(tb);
    const tagb = tags(tb);
    const inter = [...ka].filter((x) => kb.has(x)).length;
    const union = new Set([...ka, ...kb]).size;
    const score = union ? inter / union : 0;
    if (score >= 0.6) {
      const ra = relative(root, a).replace(/\\/g, "/");
      const rb = relative(root, b).replace(/\\/g, "/");
      appendFileSync(queue, `\n| ${date} | \`${ra}\` | 疑似重复 | 与 \`${rb}\` 关键词重合度 ${score.toFixed(2)} | 合并或区分边界 | 待处理 |`, "utf8");
      appendFileSync(rel, `\n| ${date} | \`${ra}\` | \`${rb}\` | 疑似重复 | 关键词重合度 ${score.toFixed(2)} |`, "utf8");
      pairs++;
    }
    const tInter = [...taga].filter((x) => tagb.has(x)).length;
    const tUnion = new Set([...taga, ...tagb]).size;
    const tScore = tUnion ? tInter / tUnion : 0;
    if (tScore >= 0.5) {
      const ra = relative(root, a).replace(/\\/g, "/");
      const rb = relative(root, b).replace(/\\/g, "/");
      appendFileSync(queue, `\n| ${date} | \`${ra}\` | 标签近邻 | 与 \`${rb}\` 标签重合度 ${tScore.toFixed(2)} | 建议检查主题聚合 | 待处理 |`, "utf8");
      appendFileSync(rel, `\n| ${date} | \`${ra}\` | \`${rb}\` | 标签近邻 | 标签重合度 ${tScore.toFixed(2)} |`, "utf8");
      tagPairs++;
    }
  }
}
process.stdout.write(JSON.stringify({ ok: true, pairs, tag_pairs: tagPairs }));
