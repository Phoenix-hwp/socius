import { existsSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn } from "node:child_process";

function loadEnvFile(envPath) {
  if (!existsSync(envPath)) return;
  const lines = readFileSync(envPath, "utf8").split(/\r?\n/);
  for (const raw of lines) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const idx = line.indexOf("=");
    if (idx <= 0) continue;
    const key = line.slice(0, idx).trim();
    let value = line.slice(idx + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    if (key && !process.env[key]) {
      process.env[key] = value;
    }
  }
}

const scriptDir = dirname(fileURLToPath(import.meta.url));
const envPath = resolve(scriptDir, "notion.env");
loadEnvFile(envPath);

if (!process.env.NOTION_TOKEN || !process.env.NOTION_TOKEN.trim()) {
  process.stderr.write(
    "[notion-mcp] Missing NOTION_TOKEN. Please copy .cursor/mcp/notion.env.example to .cursor/mcp/notion.env and fill it.\n",
  );
  process.exit(1);
}

function resolveNpx() {
  if (process.platform === "win32") {
    const defaultNpx = "C:\\Program Files\\nodejs\\npx.cmd";
    if (existsSync(defaultNpx)) return defaultNpx;
  }
  return "npx";
}

const npxCmd = resolveNpx();
const isWinCmd = process.platform === "win32" && npxCmd.toLowerCase().endsWith(".cmd");
const child = isWinCmd
  ? spawn(`"${npxCmd}"`, ["-y", "@notionhq/notion-mcp-server"], {
      cwd: scriptDir,
      stdio: "inherit",
      shell: true,
    })
  : spawn(npxCmd, ["-y", "@notionhq/notion-mcp-server"], {
      cwd: scriptDir,
      stdio: "inherit",
      shell: false,
    });

child.on("error", () => {
  process.stderr.write(
    "[notion-mcp] Missing npx. Install Node.js LTS (with npm/npx) or add npx to PATH.\n",
  );
  process.exit(1);
});

child.on("exit", (code) => {
  process.exit(code ?? 1);
});
