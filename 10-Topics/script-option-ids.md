---
Title: 脚本选项 ID 目录（Git · Notion）
Lifecycle: 阶段
Created: 2026-05-02
Updated: 2026-05-03
purpose: 对话与规则中用稳定 ID 指代脚本动作；避免仅靠自然语言触发歧义
---

# 脚本选项 ID 目录

## 1) 工作区 Git / Gitee（`git.workspace.*`）

**说明**：跨设备与工作区版本同步统一走 **Git**；口语 **`提交git`** 见 `.cursor/rules/flow-git-commit.mdc` 与 **`plans/Gitee-Workspace-Git-Workflow.md`**。

| 选项 ID | 说明 |
|---------|------|
| `git.workspace.workflow` | 备忘路径：`plans/Gitee-Workspace-Git-Workflow.md`（首次 `remote`、日常 `commit`/`push`） |
| `git.workspace.rule` | 执行级规则：`.cursor/rules/flow-git-commit.mdc` |

---

## 2) Notion 内容目录（`notion.dir.*`）

- **数据文件**：`.cursor/mcp/notion_cascader_directory_choices.json`  
- **生成规则**：由 `.cursor/mcp/notion_cascader_options.json` 展开——**有子节点则只产出叶子**；**无子节点则产出当前节点**。  
- **刷新**：在 `.cursor/mcp/` 下运行 `refresh_notion_directory_choices.cmd`（Python，失败则 Node）。

表中每条有 **`id`**（形如 `notion.dir.<uuid>`）、**`path`**（多级标签路径）、**`notionObjectType`**（`page` / `database`）、**`url`**。

对话里请直接回复选项 **`id`**，Agent 据 `id` 解析 `value`/`url` 写入 workflow 或 API，避免口述路径跑偏。

---

## 3) Notion 工作流脚本（口语映射 · 可选）

未封装单一 dispatch；需要时在仓库根或 `.cursor/mcp` 下执行：

| 选项 ID（建议口述） | 典型命令 |
|---------------------|----------|
| `notion.workflow.read` | `python .cursor/mcp/run_notion_workflow.py --config .cursor/mcp/notion_workflow.read.json --interactive` |
| `notion.workflow.sync` | `python .cursor/mcp/run_notion_workflow.py --config .cursor/mcp/notion_workflow.sync.json --interactive` |

（工作目录可按环境调整为先 `cd` 到 `.cursor/mcp`。）

| 选项 ID | 说明 |
|---------|------|
| `notion.refresh.directory_choices` | 运行 `refresh_notion_directory_choices.cmd` |
| `notion.refresh.page_tree` | 运行 `refresh_notion_page_tree.cmd`（级联源 JSON 的另一刷新链路） |

---

## 4) 维护约定

- 更新 Notion 目录结构并导出 `notion_cascader_options.json` 后，执行 **`notion.refresh.directory_choices`**（或等价命令）再提交 `notion_cascader_directory_choices.json`，保证对话里的 ID 与现网一致。
- Git 工作流变更时，同步更新 **`plans/Gitee-Workspace-Git-Workflow.md`** 与本表 **`git.workspace.*`** 说明。
