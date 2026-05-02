import { appendFileSync } from "node:fs";
import { join } from "node:path";

const d = new Date().toISOString().slice(0, 10);
const q = join(process.cwd(), "Earth_Library", "Review_Queue.md");
appendFileSync(q, `\n| ${d} | (system) | 优化建议 | 建议按主题聚合旧卡片并补充来源字段 | 执行合并前人工确认 | 待处理 |`, "utf8");
process.stdout.write(JSON.stringify({ ok: true, date: d }));
