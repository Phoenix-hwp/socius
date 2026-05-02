/**
 * Popup Notion local workflow GUI when prompt contains command keywords.
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { spawn } from "node:child_process";

const KEYWORDS = [
  "notion菜单",
  "notion 面板",
  "打开notion面板",
  "打开notion菜单",
  "同步notion",
  "notion同步",
  "notion向导",
  "notion crud",
  "notion增删改查",
];

function readPayload() {
  const raw = readFileSync(0, "utf8");
  if (!raw.trim()) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return { raw };
  }
}

function extractPrompt(payload) {
  for (const key of ["prompt", "userPrompt", "text", "input"]) {
    if (typeof payload[key] === "string") return payload[key];
  }
  try {
    return JSON.stringify(payload);
  } catch {
    return "";
  }
}

function shouldPopup(promptText) {
  const lower = String(promptText || "").toLowerCase();
  return KEYWORDS.some((k) => lower.includes(k));
}

function openGui(projectDir) {
  const script = resolve(projectDir, ".cursor", "tools", "notion_gui_menu.ps1");
  const child = spawn(
    "powershell",
    ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script],
    {
      cwd: projectDir,
      detached: true,
      stdio: "ignore",
      windowsHide: false,
    }
  );
  child.unref();
}

function main() {
  const payload = readPayload();
  const prompt = extractPrompt(payload);
  if (shouldPopup(prompt)) {
    const projectDir = process.env.CURSOR_PROJECT_DIR || process.cwd();
    openGui(projectDir);
  }
  process.stdout.write(`${JSON.stringify({ permission: "allow" })}\n`);
}

main();
