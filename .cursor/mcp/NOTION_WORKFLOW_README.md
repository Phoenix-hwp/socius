# Notion Workflow (Auto Runner)

## Routing Strategy (Plugin + Local Fallback)

- Primary route: `plugin-notion-workspace-notion` (plugin MCP service).
- Fallback route: `notion-local` (workspace local MCP server via `.cursor/mcp.json`).
- Naming rule: keep local route named `notion-local` to avoid confusion with plugin route.
- Recommended practice: use plugin route by default; switch to local route when plugin auth/service is unavailable.

Use `run_notion_workflow.py` with a JSON config to run repeatable Notion tasks.

## 0) Unified CRUD workflow (chat default + optional local menu)

**Primary**: In **Cursor chat**, follow the three-layer Notion rules:
- Layer 2 framework: `.cursor/rules/mod-notion-crud-framework.mdc` — network (**`Y`**) → numbered **directory** → branch by operation (**create / read / update / archive**)
- Layer 3 workflows:
  - **Create**: `.cursor/rules/flow-notion-create.mdc` — detail steps + **`确认写入`** **Update**: choose **`1` replace-all (clear top-level blocks then write)** vs **`2` merge/diff (fetch + partial patch per anchors / Playbook)** → preview → **`确认更新`**; **prefer Notion MCP**, scripts only as fallback with reason. **Delete** uses Notion archive + **`确认删除`** (see rule).

**Optional** local CMD wizard: `"<vault>\.cursor\mcp\notion_write_menu.cmd"` or `python notion_write_menu.py` — interactive **CRUD** (create + read summary + update + archive under chosen parent).

GUI fallback: `.cursor/tools/notion_gui_menu.ps1` (includes CRUD wizard launcher + workflow buttons + drill shortcuts).

Uses `notion_cascader_directory_choices.json`; requires `notion.env` with `NOTION_TOKEN`. Parent **page** or **database**. Title-based locate for read/update/archive uses `find_candidates_under_parent()` in `run_notion_workflow.py` (substring match; DB rows via title filter; subpages via `child_page` blocks).

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

- `archive_page`
  - Required: `target` (page URL or ID)
  - Behavior: `PATCH pages/{id}` with `archived: true` (Notion trash / soft delete).
  - With `interactive` or `confirm_execute: true`, prompts before execution.

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
