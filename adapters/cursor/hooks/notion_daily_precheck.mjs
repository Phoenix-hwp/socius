/**
 * Daily precheck hook for Notion MCP calls.
 * Runs once per day on first Notion MCP task.
 */

import { readFileSync, writeFileSync, appendFileSync, mkdirSync, existsSync, writeSync } from "node:fs";
import { join } from "node:path";
import { lookup } from "node:dns/promises";
import { platform } from "node:os";
import { spawnSync } from "node:child_process";
import { runFix } from "./notion_auth_oneclick_fix.mjs";

const STATE_PATH = join("Daily-Backups", "TMP_notion_precheck_state.json");
const LOG_PATH = join("Daily-Backups", "TMP_notion_precheck_log.jsonl");

function emit(payload) {
  writeSync(1, Buffer.from(`${JSON.stringify(payload)}\n`, "utf8"));
}

function readPayload() {
  const raw = readFileSync(0, "utf8");
  if (!raw.trim()) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return { raw_input: raw, parse_error: true };
  }
}

function projectRoot() {
  return process.env.CURSOR_PROJECT_DIR || process.cwd();
}

function readJson(filePath) {
  if (!existsSync(filePath)) return {};
  try {
    return JSON.parse(readFileSync(filePath, "utf8"));
  } catch {
    return {};
  }
}

function writeJson(filePath, payload) {
  mkdirSync(join(projectRoot(), "Daily-Backups"), { recursive: true });
  writeFileSync(filePath, JSON.stringify(payload, null, 2), "utf8");
}

function appendLog(filePath, payload) {
  mkdirSync(join(projectRoot(), "Daily-Backups"), { recursive: true });
  appendFileSync(filePath, `${JSON.stringify(payload)}\n`, "utf8");
}

function isNotionMcp(payload) {
  return JSON.stringify(payload).toLowerCase().includes("notion");
}

function extractToolName(payload) {
  return payload.toolName || payload.tool_name || payload.mcp_tool_name || payload.name || "";
}

function todayDate() {
  return new Date().toISOString().slice(0, 10);
}

function alreadyCheckedToday(state) {
  return state.date === todayDate() && state.ok === true;
}

async function checkDns() {
  try {
    await lookup("www.notion.so");
    return { name: "dns_resolve_notion", ok: true, detail: "dns_ok" };
  } catch (err) {
    return { name: "dns_resolve_notion", ok: false, detail: `dns_failed:${String(err)}` };
  }
}

function checkHttpsAssociation() {
  if (platform() !== "win32") {
    return { name: "https_default_browser_association", ok: true, detail: "skip_non_windows" };
  }
  try {
    const proc = spawnSync(
      "reg",
      [
        "query",
        "HKCU\\Software\\Microsoft\\Windows\\Shell\\Associations\\UrlAssociations\\https\\UserChoice",
        "/v",
        "ProgId",
      ],
      { encoding: "utf8", timeout: 6000 }
    );
    if ((proc.status ?? 1) !== 0) {
      return {
        name: "https_default_browser_association",
        ok: false,
        detail: `https_assoc_query_failed:${proc.status}`,
      };
    }
    if (!String(proc.stdout || "").includes("ProgId")) {
      return {
        name: "https_default_browser_association",
        ok: false,
        detail: "https_assoc_missing_progid",
      };
    }
    return { name: "https_default_browser_association", ok: true, detail: "https_assoc_ok" };
  } catch (err) {
    return {
      name: "https_default_browser_association",
      ok: false,
      detail: `https_assoc_failed:${String(err)}`,
    };
  }
}

function checkInteractiveSession() {
  const session = process.env.SESSIONNAME || "";
  if (!session) {
    return { name: "interactive_desktop_session", ok: true, detail: "session_unknown" };
  }
  if (session.toLowerCase().includes("service")) {
    return { name: "interactive_desktop_session", ok: false, detail: `non_interactive_session:${session}` };
  }
  return { name: "interactive_desktop_session", ok: true, detail: `interactive_session:${session}` };
}

async function runPrecheck() {
  const checks = [await checkDns(), checkHttpsAssociation(), checkInteractiveSession()];
  return { ok: checks.every((c) => c.ok), checks };
}

async function main() {
  const payload = readPayload();
  if (!isNotionMcp(payload)) {
    emit({ permission: "allow" });
    return;
  }

  const toolName = extractToolName(payload);
  if (toolName === "mcp_auth") {
    emit({ permission: "allow" });
    return;
  }

  const root = projectRoot();
  const stateFile = join(root, STATE_PATH);
  const logFile = join(root, LOG_PATH);
  const state = readJson(stateFile);
  if (alreadyCheckedToday(state)) {
    emit({ permission: "allow" });
    return;
  }

  const precheck = await runPrecheck();
  const now = new Date().toISOString();
  const logEntry = {
    time: now,
    kind: "notion_daily_precheck",
    ok: precheck.ok,
    tool_name: toolName,
    checks: precheck.checks,
  };

  if (precheck.ok) {
    writeJson(stateFile, { date: todayDate(), ok: true, updated_at: now });
    appendLog(logFile, logEntry);
    emit({ permission: "allow" });
    return;
  }

  const fix = runFix();
  logEntry.fix = fix;
  writeJson(stateFile, {
    date: todayDate(),
    ok: false,
    updated_at: now,
    last_error: precheck.checks,
    fix,
  });
  appendLog(logFile, logEntry);
  emit({
    permission: "ask",
    user_message:
      "Notion 每日预检失败，已自动触发一键修复（浏览器唤起预热）。请确认网络与默认浏览器后，先执行一次 mcp_auth。",
    agent_message: "Notion daily precheck failed and auto-repair was executed.",
  });
}

main();
