import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const q = join(process.cwd(), "Earth_Library", "Review_Queue.md");
const txt = readFileSync(q, "utf8");
writeFileSync(q, txt.replace(/\| 待处理 \|/g, "| 已处理建议 |"), "utf8");
process.stdout.write(JSON.stringify({ ok: true, mode: "mark_suggested" }));
