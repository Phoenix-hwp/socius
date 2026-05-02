/**
 * Project sessionStart hook: inject Obsidian profile (same logic as .py).
 * Direct: node .cursor/hooks/session_start_profile_context.mjs
 * Default entry: node .cursor/hooks/session_start_profile_launch.mjs (Python first, then this file).
 * Cursor sets CURSOR_PROJECT_DIR; override profile with CURSOR_OBSIDIAN_PROFILE.
 */

import { readFileSync, existsSync, writeSync } from "node:fs";
import { join } from "node:path";

const MAX_CHARS = 20000;

/** Windows defaults stdout to a legacy code page; Cursor expects UTF-8 JSON. */
function emitJson(payload) {
  writeSync(1, Buffer.from(`${JSON.stringify(payload)}\n`, "utf8"));
}

const REL_PROFILE_CANDIDATES = [
  join("Cursor_Knowledge", "10-Topics", "Cursor-usage-profile-and-templates.md"),
  join("10-Topics", "Cursor-usage-profile-and-templates.md"),
];

function resolveProfilePath() {
  const override = process.env.CURSOR_OBSIDIAN_PROFILE;
  if (override) {
    if (existsSync(override)) return { path: override, err: null };
    return {
      path: null,
      err: `CURSOR_OBSIDIAN_PROFILE is set but not a file: ${override}`,
    };
  }

  const root = process.env.CURSOR_PROJECT_DIR || process.cwd();
  for (const rel of REL_PROFILE_CANDIDATES) {
    const candidate = join(root, rel);
    if (existsSync(candidate)) return { path: candidate, err: null };
  }

  const tried = REL_PROFILE_CANDIDATES.map((r) => join(root, r)).join(", ");
  return {
    path: null,
    err: `No profile at any of: ${tried}. CURSOR_PROJECT_DIR=${JSON.stringify(
      root
    )}. Set CURSOR_OBSIDIAN_PROFILE to an existing .md, or add the profile file.`,
  };
}

function main() {
  const { path, err } = resolveProfilePath();
  if (!path) {
    const msg = "## sessionStart hook (project)\n\n" + (err || "Profile not found.");
    emitJson({ additional_context: msg });
    return;
  }

  let text = readFileSync(path, "utf8");
  if (text.length > MAX_CHARS) {
    text =
      text.slice(0, MAX_CHARS) +
      "\n\n[truncated by sessionStart hook; open profile file for full text]\n";
  }

  const ctx =
    "## Injected by sessionStart hook (Obsidian profile)\n\n" +
    text +
    "\n\n---\n" +
    "Workflow: On wrap-up, user sends `/收束`, `会话收束：`, `结束会话`, or `结束对话`; append one row to §6; " +
    "update §5 if needed.\n";

  emitJson({ additional_context: ctx });
}

try {
  main();
} catch (exc) {
  emitJson({ additional_context: `sessionStart hook error: ${exc}` });
  process.exitCode = 0;
}
