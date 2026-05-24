/**
 * Flatten cascader JSON to leaf-level directory choices (mirror of notion_cascader_leaves.py).
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** @param {Record<string, unknown>} node */
/** @param {string[]} pathParts */
function* iterLeaves(node, pathParts) {
  if (node.disabled) return;
  const label = String(node.label ?? "").trim();
  const parts = label ? [...pathParts, label] : [...pathParts];
  const rawChildren = node.children;
  const children = Array.isArray(rawChildren) ? rawChildren : [];

  if (children.length === 0) {
    const stable = String(node.value ?? node.id ?? "").trim();
    if (!stable) return;
    yield {
      id: `notion.dir.${stable}`,
      path: parts.join("/"),
      label: label || stable,
      notionObjectType: node.notionObjectType ?? node.nodeType,
      nodeType: node.nodeType,
      value: stable,
      url: node.url ?? "",
    };
    return;
  }

  for (const ch of children) {
    if (ch && typeof ch === "object") yield* iterLeaves(/** @type {Record<string, unknown>} */ (ch), parts);
  }
}

function main() {
  const argv = process.argv.slice(2);
  let input = "notion_cascader_options.json";
  let output = "notion_cascader_directory_choices.json";
  let stdout = false;
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--input" && argv[i + 1]) input = argv[++i];
    else if (argv[i] === "--output" && argv[++i]) output = argv[++i];
    else if (argv[i] === "--stdout") stdout = true;
  }

  const inPath = path.isAbsolute(input) ? input : path.join(__dirname, input);
  if (!fs.existsSync(inPath)) {
    console.log(JSON.stringify({ ok: false, error: `Input not found: ${inPath}` }));
    process.exit(1);
  }

  const doc = JSON.parse(fs.readFileSync(inPath, "utf8"));
  const options = Array.isArray(doc.options) ? doc.options : [];
  const rows = [];
  for (const root of options) {
    if (root && typeof root === "object") rows.push(...iterLeaves(/** @type {Record<string, unknown>} */ (root), []));
  }
  rows.sort((a, b) => (a.path || "").localeCompare(b.path || "", "en"));

  const outDoc = {
    schemaVersion: "1.0.0",
    generatedAt: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    sourceFile: path.relative(__dirname, inPath),
    description:
      "Leaf-level Notion directory targets; use id in conversation for disambiguation.",
    options: rows,
  };

  const text = JSON.stringify(outDoc, null, 2);
  if (stdout) {
    console.log(text);
    process.exit(0);
  }
  const outPath = path.isAbsolute(output) ? output : path.join(__dirname, output);
  fs.writeFileSync(outPath, text + "\n", "utf8");
  console.log(JSON.stringify({ ok: true, output_file: outPath, count: rows.length }));
}

main();
