/**
 * sessionStart shim: try Python implementation, then Node (.mjs).
 * Avoids registering two sessionStart hooks (duplicate injection risk).
 * hooks.json: prefer ``cmd /c python ...launch.py || node ...launch.mjs`` (Windows)
 * or ``python`` / ``node`` alone; see hooks.json in this repo.
 */

import { spawnSync } from "node:child_process";
import { writeSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const pyScript = join(__dirname, "session_start_profile_context.py");
const mjsScript = join(__dirname, "session_start_profile_context.mjs");

/** @returns {string | null} raw stdout line(s) to forward */
function tryRun(command, args) {
  const r = spawnSync(command, args, {
    encoding: "buffer",
    env: process.env,
    shell: false,
  });
  if (r.error?.code === "ENOENT") return null;
  if (r.status !== 0) return null;
  const buf = r.stdout;
  if (!buf || !buf.length) return null;
  const out = buf.toString("utf8").trim();
  if (!out) return null;
  try {
    const j = JSON.parse(out);
    if (j && typeof j.additional_context === "string") return out;
  } catch {
    return null;
  }
  return null;
}

const attempts = [
  ["python", [pyScript]],
  ["python3", [pyScript]],
];
if (process.platform === "win32") {
  attempts.push(["py", ["-3", pyScript]]);
}
attempts.push(["node", [mjsScript]]);

for (const [cmd, args] of attempts) {
  const out = tryRun(cmd, args);
  if (out) {
    const line = out.endsWith("\n") ? out : `${out}\n`;
    writeSync(1, Buffer.from(line, "utf8"));
    process.exit(0);
  }
}

writeSync(
  1,
  Buffer.from(
    `${JSON.stringify({
      additional_context:
        "## sessionStart hook (project)\n\n" +
        "Could not run a working `python` / `python3` / `py -3` or `node` for the profile hook. " +
        "Install [Python](https://www.python.org/downloads/) or [Node](https://nodejs.org/), " +
        "or set `CURSOR_OBSIDIAN_PROFILE` and use a one-line hook that only fits your environment.",
    })}\n`,
    "utf8"
  )
);
process.exit(0);
