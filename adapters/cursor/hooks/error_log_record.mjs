/**
 * Project hook: persist task errors with environment metadata.
 */

import { appendFileSync, mkdirSync, readFileSync, writeSync } from "node:fs";
import { join } from "node:path";
import os from "node:os";

const LOG_REL_PATH = join("Knowledge-Assets", "Error-Logs", "Task_Error_Log.jsonl");

function safeJsonParse(raw) {
  if (!raw || !raw.trim()) return {};
  try {
    return JSON.parse(raw);
  } catch {
    return { raw_stdin: raw, parse_error: "invalid_json" };
  }
}

function detectFailure(payload) {
  const event = String(payload.hook_event_name || payload.eventName || "");
  if (event === "postToolUseFailure") {
    return [true, "postToolUseFailure"];
  }
  if (event === "afterShellExecution") {
    const exitCode = payload.exit_code;
    if (Number.isInteger(exitCode) && exitCode !== 0) {
      return [true, "afterShellExecution.nonzero_exit"];
    }
    return [false, "afterShellExecution.ok"];
  }
  if (payload.error || payload.is_error === true) {
    return [true, "payload.error_flag"];
  }
  return [false, "not_error"];
}

function buildRecord(payload, reason) {
  const now = new Date();
  return {
    timestamp_utc: now.toISOString(),
    timestamp_local: now.toString(),
    reason,
    environment: {
      os: os.platform(),
      os_release: os.release(),
      architecture: os.arch(),
      node_version: process.version,
      hostname: os.hostname(),
      username: process.env.USERNAME || process.env.USER,
      cursor_project_dir: process.env.CURSOR_PROJECT_DIR,
      cwd: process.cwd(),
    },
    event: payload,
  };
}

function appendJsonl(record) {
  const root = process.env.CURSOR_PROJECT_DIR || process.cwd();
  const logPath = join(root, LOG_REL_PATH);
  mkdirSync(join(root, "Knowledge-Assets", "Error-Logs"), { recursive: true });
  appendFileSync(logPath, `${JSON.stringify(record)}\n`, "utf8");
}

function main() {
  const raw = readFileSync(0, "utf8");
  const payload = safeJsonParse(raw);
  const [shouldLog, reason] = detectFailure(payload);
  if (shouldLog) {
    appendJsonl(buildRecord(payload, reason));
  }
  writeSync(1, Buffer.from('{"permission":"allow"}\n', "utf8"));
}

main();
