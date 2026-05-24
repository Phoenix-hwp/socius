import fs from "node:fs";
import path from "node:path";

function readHead(filePath, lines = 30) {
  const text = fs.readFileSync(filePath, "utf8");
  return text.split(/\r?\n/).slice(0, lines).join("\n");
}

function isTempFile(filePath) {
  const base = path.basename(filePath);
  if (base.startsWith("TMP_")) return true;
  const head = readHead(filePath);
  return head.includes("Lifecycle: 临时");
}

function moveSoftDelete(src, trashRoot) {
  const ext = path.extname(src);
  const stem = path.basename(src, ext);
  let target = path.join(trashRoot, path.basename(src));
  if (fs.existsSync(target)) {
    const stamp = new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 14);
    target = path.join(trashRoot, `${stem}_${stamp}${ext}`);
  }
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.renameSync(src, target);
  return target;
}

const argDays = process.argv.find((a) => a.startsWith("--days="));
const days = argDays ? Number(argDays.split("=")[1]) : 15;
const now = Date.now();
const cutoff = now - days * 24 * 60 * 60 * 1000;

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..", "..").replace(/^\/([A-Za-z]:)/, "$1");
const dailyDir = path.join(root, "Daily-Backups");
const trashDir = path.join(root, ".trash", "soft-delete", "daily-backups");

if (!fs.existsSync(dailyDir)) {
  console.log("No Daily-Backups directory found.");
  process.exit(0);
}

const moved = [];
for (const name of fs.readdirSync(dailyDir)) {
  if (!name.endsWith(".md")) continue;
  if (name === "日常备份索引.md") continue;
  const full = path.join(dailyDir, name);
  if (!isTempFile(full)) continue;
  const stat = fs.statSync(full);
  if (stat.mtimeMs <= cutoff) {
    const target = moveSoftDelete(full, trashDir);
    moved.push({ name, target });
  }
}

console.log(`Scanned: ${dailyDir}`);
console.log(`Retention days: ${days}`);
console.log(`Moved count: ${moved.length}`);
for (const item of moved) {
  console.log(`- ${item.name} -> ${item.target}`);
}
