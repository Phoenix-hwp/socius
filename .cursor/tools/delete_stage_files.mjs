import fs from "node:fs";
import path from "node:path";
import readline from "node:readline";

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..", "..").replace(/^\/([A-Za-z]:)/, "$1");
const whitelistPath = path.join(root, ".cursor", "config", "stage-delete-whitelist.txt");
const trashRoot = path.join(root, ".trash", "soft-delete", "stage-files");

function readWhitelist(filePath) {
  return fs
    .readFileSync(filePath, "utf8")
    .split(/\r?\n/)
    .map((s) => s.trim())
    .filter((s) => s && !s.startsWith("#"));
}

function isStageFile(filePath) {
  if (path.basename(filePath).startsWith("STAGE_")) return true;
  const head = fs.readFileSync(filePath, "utf8").split(/\r?\n/).slice(0, 30).join("\n");
  return head.includes("Lifecycle: 阶段");
}

function collectCandidates() {
  const out = [];
  for (const rel of readWhitelist(whitelistPath)) {
    const base = path.join(root, rel);
    if (!fs.existsSync(base) || !fs.statSync(base).isDirectory()) continue;
    const stack = [base];
    while (stack.length) {
      const dir = stack.pop();
      for (const name of fs.readdirSync(dir)) {
        const full = path.join(dir, name);
        const st = fs.statSync(full);
        if (st.isDirectory()) stack.push(full);
        else if (name.endsWith(".md") && isStageFile(full)) out.push(full);
      }
    }
  }
  return out;
}

function softDelete(src) {
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

function ask(question, rl) {
  return new Promise((resolve) => rl.question(question, resolve));
}

if (!fs.existsSync(whitelistPath)) {
  console.error("Whitelist file missing:", whitelistPath);
  process.exit(1);
}

const candidates = collectCandidates();
if (!candidates.length) {
  console.log("No stage files found in whitelist paths.");
  process.exit(0);
}

console.log("Stage-file candidates:");
candidates.forEach((c, idx) => console.log(`${String(idx + 1).padStart(3, " ")}. ${path.relative(root, c)}`));

const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
const yes = await ask("Type YES to continue to final confirmation: ", rl);
if (yes.trim() !== "YES") {
  console.log("Cancelled.");
  rl.close();
  process.exit(0);
}
const confirm = await ask("Type CONFIRM to soft-delete the above files: ", rl);
rl.close();
if (confirm.trim() !== "CONFIRM") {
  console.log("Cancelled.");
  process.exit(0);
}

const moved = candidates.map((src) => ({ src, dst: softDelete(src) }));
console.log(`Moved count: ${moved.length}`);
moved.forEach(({ src, dst }) => {
  console.log(`- ${path.relative(root, src)} -> ${path.relative(root, dst)}`);
});
