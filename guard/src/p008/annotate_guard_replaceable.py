"""Batch-annotate guard_replaceable to all .mdc rules in .cursor/rules/.

Reads each .mdc file, adds `guard_replaceable: <value>` to frontmatter YAML.
Operates on a pre-classified mapping dict. Idempotent — skips if already present.
"""

import os
from pathlib import Path

RULES_DIR = Path(os.environ.get("CURSOR_PROJECT_DIR", os.getcwd())) / ".cursor" / "rules"

# ── Classification mapping ──────────────────────────────────────
# Each entry: filename -> guard_replaceable value
CLASSIFICATION: dict[str, str] = {
    # Safety (alwaysApply: true) — 7 files
    "flow-high-risk-safety.mdc":             "true",
    "data-governance-standards.mdc":         "partial",
    "external-dependency-boundary.mdc":       "false",
    "git-cross-device-and-secrets.mdc":       "partial",
    "pre-change-impact-enumeration.mdc":     "partial",
    "pre-edit-script-change-brief.mdc":      "false",
    "script-coding-constraints.mdc":         "partial",

    # Conditional — 4 files
    "ask-question-mandate.mdc":              "true",
    "default-chinese-output-for-english-responses.mdc": "false",
    "kernel-runtime.mdc":                    "false",
    "lifecycle-storage-and-cleanup.mdc":     "partial",

    # Gateway (Layer 1) — 2 files
    "gateway-command-router.mdc":            "false",
    "task-init-protocol.mdc":               "false",

    # Module Framework (Layer 2) — 11 files
    "mod-behavior-crud-framework.mdc":       "framework",
    "mod-conversation-framework.mdc":        "framework",
    "mod-decision-framework.mdc":            "framework",
    "mod-multi-round-framework.mdc":         "framework",
    "mod-notion-crud-framework.mdc":         "framework",
    "mod-notion-precondition.mdc":           "partial",
    "mod-project-memo-framework.mdc":        "framework",
    "mod-simulation-framework.mdc":          "framework",
    "mod-skill-evaluation.mdc":              "framework",
    "mod-skills-library-framework.mdc":      "framework",
    "mod-system-audit.mdc":                  "framework",

    # Workflow (Layer 3) — 22 files
    "flow-behavior-auto-receipt.mdc":        "false",
    "flow-capability-encapsulate.mdc":       "false",
    "flow-conversation-backup.mdc":          "partial",
    "flow-conversation-read.mdc":            "false",
    "flow-conversation-resume.mdc":          "false",
    "flow-conversation-routing.mdc":         "false",
    "flow-multi-round-upgrade.mdc":          "false",
    "flow-notion-create.mdc":                "false",
    "flow-notion-delete.mdc":                "false",
    "flow-notion-locate-target.mdc":         "false",
    "flow-notion-query.mdc":                 "false",
    "flow-notion-select-parent.mdc":         "false",
    "flow-notion-update.mdc":                "false",
    "flow-project-memo-append.mdc":          "false",
    "flow-project-memo-read.mdc":            "false",
    "flow-simulation-execute.mdc":           "false",
    "flow-skill-acquire.mdc":                "false",
    "flow-skill-execute.mdc":                "partial",
    "flow-skill-toggle.mdc":                 "false",
    "flow-v012-drill-bridge.mdc":            "false",
    "flow-v012-pipeline-execute.mdc":        "partial",
}


def annotate_file(filepath: Path, value: str) -> str:
    """Read file, insert guard_replaceable into frontmatter, return action description."""
    content = filepath.read_text(encoding="utf-8")
    
    # Check if already annotated
    if "guard_replaceable:" in content:
        return "skip (already annotated)"
    
    # Find the first --- closing delimiter (end of frontmatter)
    first_close = content.find("---", 1)  # skip opening ---
    if first_close == -1:
        return "fail (no frontmatter)"
    
    # Find the last line before closing ---
    before_close = content[:first_close].rstrip()
    # Determine indentation of the last field before ---
    lines = before_close.split("\n")
    last_field = lines[-1]
    indent = ""
    
    # Insert guard_replaceable before the closing ---
    new_frontmatter = before_close + f"\n{indent}guard_replaceable: {value}\n"
    new_content = new_frontmatter + content[first_close:]
    
    filepath.write_text(new_content, encoding="utf-8")
    return f"added guard_replaceable: {value}"


def main():
    results = {"added": [], "skip": [], "fail": [], "missing": []}
    
    for filename, value in sorted(CLASSIFICATION.items()):
        filepath = RULES_DIR / filename
        if not filepath.exists():
            results["missing"].append(filename)
            print(f"  MISSING: {filename}")
            continue
        
        action = annotate_file(filepath, value)
        if "added" in action:
            results["added"].append(f"{filename} -> {value}")
        elif "skip" in action:
            results["skip"].append(filename)
        else:
            results["fail"].append(filename)
        print(f"  {action.upper()}: {filename}")
    
    print(f"\n{'='*50}")
    print(f"  Added:    {len(results['added'])}")
    print(f"  Skipped:  {len(results['skip'])}")
    print(f"  Failed:   {len(results['fail'])}")
    print(f"  Missing:  {len(results['missing'])}")
    return 0 if not results["fail"] and not results["missing"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
