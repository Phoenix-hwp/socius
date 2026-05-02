/**
 * One-click repair for Notion auth window issues.
 */
import { platform } from "node:os";
import { spawnSync } from "node:child_process";

export function runFix() {
  const actions = [];
  if (platform() === "win32") {
    try {
      const proc = spawnSync(
        "powershell",
        ["-NoProfile", "-Command", "Start-Process 'https://www.notion.so/'"],
        {
          encoding: "utf8",
          timeout: 6000,
        }
      );
      actions.push({
        name: "warmup_browser",
        ok: (proc.status ?? 1) === 0,
        code: proc.status,
      });
    } catch (err) {
      actions.push({
        name: "warmup_browser",
        ok: false,
        error: String(err),
      });
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
        {
        encoding: "utf8",
          timeout: 6000,
        }
      );
      actions.push({
        name: "verify_https_association",
        ok: (proc.status ?? 1) === 0 && String(proc.stdout || "").includes("ProgId"),
        code: proc.status,
      });
    } catch (err) {
      actions.push({
        name: "verify_https_association",
        ok: false,
        error: String(err),
      });
    }
  } else {
    actions.push({
      name: "warmup_browser",
      ok: false,
      error: "one-click fix currently targets Windows launcher path",
    });
  }
  return { ok: actions.every((a) => a.ok), actions };
}
