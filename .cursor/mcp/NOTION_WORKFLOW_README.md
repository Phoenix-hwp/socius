# Notion Workflow (Auto Runner)

## Routing Strategy (Plugin + Local Fallback)

- Primary route: `plugin-notion-workspace-notion` (plugin MCP service).
- Fallback route: `notion-local` (workspace local MCP server via `.cursor/mcp.json`).
- Naming rule: keep local route named `notion-local` to avoid confusion with plugin route.
- Recommended practice: use plugin route by default; switch to local route when plugin auth/service is unavailable.

Use `run_notion_workflow.py` with a JSON config to run repeatable Notion tasks.

## 0) Interactive write wizard (chat default + optional local menu)

**Primary**: In **Cursor chat**, follow the **fixed 6-step** flow in `.cursor/rules/notion-write-workflow-confirmation.mdc` (network → numbered directory → title mode 1/2 → title resolution → **body preview** → user says **`确认写入`** → API). No requirement to use an external terminal for Notion writes.

**Optional** local CMD wizard (same semantics): `"<vault>\.cursor\mcp\notion_write_menu.cmd"` or `python notion_write_menu.py` under `.cursor/mcp`.

Optional GUI fallback: `.cursor/tools/notion_gui_menu.ps1` (workflow buttons + drill shortcuts).

Uses `notion_cascader_directory_choices.json`; requires `notion.env` with `NOTION_TOKEN`. Supports parent **page** or **database** (`do_create_page` in `run_notion_workflow.py`).

## 1) Prepare config

Copy:

- `.cursor/mcp/notion_workflow.template.json` -> `.cursor/mcp/notion_workflow.json`

Then edit fields by mode.

If your terminal has Chinese encoding issues, set `output_file` in config and read that UTF-8 file.

## 2) Run

```powershell
python ".cursor/mcp/run_notion_workflow.py" --config ".cursor/mcp/notion_workflow.json"
```

## 3) Modes

- `read`
  - Required: `target`
  - Behavior: parse URL/ID -> try database read -> fallback page read -> output summary.

- `create_page`
  - Required: `parent`, `title`, `content_file`
  - Behavior: create page under parent **page** or new row under parent **database** (auto-detect via API) → convert markdown → append blocks in batches.

- `update_page`
  - Required: `target`, `content_file`
  - Optional: `replace` (default `false`)
  - Behavior:
    - `replace=false`: append content
    - `replace=true`: archive top-level blocks first, then append content

- `sync_topic` (generic project/topic sync)
  - Fields: `action` (`update_page` or `create_page`) + corresponding fields
  - Best with `interactive: true` (or `--interactive`)
  - Behavior: asks for missing fields in CLI, then runs create/update.

## 3.1 Ready-made configs

- Read-only: `.cursor/mcp/notion_workflow.read.json`
- Generic sync: `.cursor/mcp/notion_workflow.sync.json`

Run examples:

```powershell
python ".cursor/mcp/run_notion_workflow.py" --config ".cursor/mcp/notion_workflow.read.json" --interactive
python ".cursor/mcp/run_notion_workflow.py" --config ".cursor/mcp/notion_workflow.sync.json" --interactive
```

## 4) Stability notes

- Keeps the same ID parsing strategy used in current tests.
- Uses retries and backoff for transient network errors.
- Reads token from `.cursor/mcp/notion.env` (`NOTION_TOKEN`).
- Uses UTF-8 file input for markdown to avoid terminal Chinese encoding issues.


## 5) Safety switches

- `dry_run: true` => only output execution plan, no write.
- `confirm_execute: true` => always ask for final yes/no before write execution.
- In interactive mode, write flows will display execution plan before confirmation.

## 6) Drill quick commands (no write impact)

From `.cursor/mcp` directory, run:

```powershell
.\drill-read.cmd
.\drill-create.cmd
.\drill-update.cmd
```

- `drill-read.cmd`: read-only verification (calls Notion read APIs).
- `drill-create.cmd`: create flow dry-run only (no create is executed).
- `drill-update.cmd`: update flow dry-run only (no update is executed).
