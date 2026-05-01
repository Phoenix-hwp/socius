---
title: Cursor 工作间 · Notion 作业模块 — 执行规格
Lifecycle: 阶段
created: 2026-05-01
updated: 2026-05-01
purpose: 供 Plan / Agent 研发落地；范围仅限 Notion 作业模块 MVP
---

# Cursor 工作间 · Notion 作业模块 — 执行规格

> **读者**：进入 Plan / Agent 模式后的执行者。  
> **原则**：本文与对话中已确认约定一致；冲突时以 **用户当轮明确指令** 为准。  
> **任务拆解与续跑**：见 **[Cursor-Workspace-Notion-Plan-Tasks.md](./Cursor-Workspace-Notion-Plan-Tasks.md)**（含新对话开场模板与进度表）。

---

## 1. 文档目的

- 将 **Notion 作业** 模块从原型推进到 **可测试的 MVP**（本地图形界面 + Notion API / 既有脚本能力）。
- 统一 **Agent 协作方式、目录数据、列表规则、日志策略、行为偏好页例外**，避免实现阶段口径漂移。

---

## 2. 范围与非目标

### 2.1 本期在范围内

- 侧栏模块：**Notion 作业**（完整 MVP）。
- 界面能力（对齐已确认原型）：
  - **列表态**：级联路径 + 筛选/查询 + 表格 + 分页 + 行内 **查看 / 更新**。
  - **新增页**：标题、所属目录、内容详情；**不**在表单内做 Agent 流式回显。
  - **更新页**：标题、所属目录、更新详情；**覆盖** / **补充** 二选一。
  - **操作日志**：持久化 + 保留策略 + 列表区展示规则。
- **第一张（目录树 + 工具条）原型调整**：去掉顶栏 **「更新」**；更新 **仅** 从列表行 **「更新」** 进入更新页。

### 2.2 本期不在范围内（占位即可）

- **网盘同步**、**地球图书馆**、**项目资料库**：侧栏可占位或隐藏，**不**在本期实现业务逻辑。

### 2.3 后续迭代（不阻塞 MVP）

- 各模块逐一补充；目录在 Notion 中人工维护后，通过 **约定路径拉取** 刷新本地级联 JSON。

---

## 3. Agent 与提交流程（硬约定）

| 项 | 约定 |
|----|------|
| Agent | **直接使用 Cursor 内置 Agent**（侧边栏对话），工作流围绕 Cursor。 |
| 表单与 Agent | **不在**「内容详情 / 更新详情」中做实时流式回显；由用户在 Agent 中完成任务后，通过 **对话指令** 将结果 **回写** 到表单或指定位置。 |
| 提交 | **新增 / 更新 / 覆盖 / 补充** 等写 Notion 操作，**一律由用户手动确认后执行**（点击提交类按钮）。 |
| 实现形态 | 工具 **主要给自己在 Cursor 中使用**；开发与使用不离开工作区。 |

### 3.1 图形界面 + Notion 架构（技术决议 · 已确认）

> 场景：**多设备运行、切换时尽量少配置**；**仅自用、不对外分发**。  
> 与 Ask 模式结论对齐：**Token 不进 git；本机 API 读 env；路径不写死盘符**。

| 项 | 决议 |
|----|------|
| 总体 | **本地小型 HTTP API（Python 或 Node）+ 前端（推荐 Vite/React）**；浏览器只调 `localhost`，**Notion Integration Token 仅由后端读取**，不进入前端打包产物。 |
| Token | 路径约定：**工作区相对路径** `.cursor/mcp/notion.env`（`NOTION_TOKEN`）；**不入 git**（与现有习惯一致）。换设备：**拉仓库 + 本机放一份 env + 安装依赖** 即可；无法省掉「每机一份密钥」，但可省掉 OAuth/多账户等复杂配置。 |
| 跨设备 | 新应用内**避免写死盘符**（如 `D:\`）；配置与日志路径均相对仓库根或环境变量（与 rclone 等脚本教训一致）。 |
| 不推荐 | **纯浏览器直连 Notion REST API**（Token 进前端构建或暴露于 DevTools、CORS/代理折腾），**自用多设备场景也不优先**。 |
| 模板文件 | 使用已有 **`.cursor/mcp/notion.env.example`**（仅变量名与注释，无密钥）；换机时复制为 **`.cursor/mcp/notion.env`** 再填 Token。 |
| Canvas | 可选；若需**系统浏览器调试**或与 Cursor 解耦运行，**优先 Vite + 本机 API**。自用无需 Docker/多租户。 |

---

## 4. 目录与级联数据源

| 项 | 约定 |
|----|------|
| 权威文件 | `.cursor/mcp/notion_cascader_options.json` |
| 结构 | `options[]` 顶层为 **根节点**；每节点含 `label`、`value`（稳定 id）、`nodeType`、`notionObjectType`、`id`、`url`、`children` 等；详见文件内 `fieldGuide`。 |
| 生成时间参考 | 文件内 `generatedAt`（例：2026-04-30）；更新目录后 **重新生成或手工合并** 该 JSON，并 **git 同步** 以跨设备。 |
| Notion 侧维护 | 用户在 Notion **手动** 调整结构；客户端 **拉取/刷新** 本地 JSON，**不**要求首期做复杂「目录管理」后台。 |

---

## 5. 列表与「全部」聚合

| 项 | 约定 |
|----|------|
| 列表过滤 | 由输入框前 **级联选择器** 选中的「所属目录」驱动。 |
| **全部** | 表示聚合 **`notion_cascader_options.json` 中全部顶层根节点**（当前文件为 **7** 个根：收集器、日程清单、产品研发、项目计划、Notion_Knowledge、悦读笔记、参考文摘）。 |
| 指定目录 | 选中某一叶子（或约定层级）时，列表对应 **单个 Notion 页面或单个数据库**（与 JSON 中 `notionObjectType` / `id` 一致）。 |
| 多源聚合 | 「全部」模式下对 **多个数据源** 查询后合并（见 **§5.1**）。 |

### 5.1 「全部」MVP 聚合规则（技术决议 · 已确认）

| 项 | 决议 |
|----|------|
| 数据源范围 | 从 `notion_cascader_options.json` **递归收集**所有 `notionObjectType === "database"` 的节点 `id`，对每个 id 调用 Notion **`databases/query`**；**不**对 `page` 节点做子块爬取（避免首期工期膨胀）。 |
| 合并排序 | 各库结果合并后，统一按 **`last_edited_time` 降序**（若无则回退 `created_time`）。 |
| 去重 | 以 **Notion 页面（行）`id`** 为键；同一 id 只保留一条（理论上不应跨库重复，若出现取已合并集合中任意一条即可）。 |
| 分页 | MVP：**合并后内存分页**或**游标聚合**二选一；须在 README 注明单页条数上限与「全部」模式总条数上限（若有）。 |
| `page` 节点 | 级联选中 **单个 page 型叶子** 时：列表规则在 **§6.1** 与写入分型一并实现（可与「仅 DB 出列表」的 MVP 折中：page 首版仅详情/占位提示）。 |
| 展示与数据 | **界面可统一成「表格行」**；**禁止**在合并或分页时丢弃 **`object`、`id`、所属 `database_id`（库内行来自 `parent.database_id`）** 等元数据，否则后续 **更新属性 / 区分容器与行** 会失败（见 **§6.1**）。 |

---

## 6. 新增 / 更新 / 覆盖 / 补充

| 操作 | 约定 |
|------|------|
| 新增 | 提交后在 Notion **创建**内容；父级/数据库由级联选中项解析。 |
| 更新（入口） | **仅** 列表行内 **「更新」** → 更新页。 |
| 覆盖 | 对应 Notion **替换**既有正文语义（与现有 `replace=true` 类行为对齐时需再对 API 字段）。 |
| 补充 | 对应 Notion **追加**语义（`replace=false` / append）。 |
| 实现参考 | 工作区已有：`.cursor/mcp/run_notion_workflow.py`、`NOTION_WORKFLOW_README.md`、Notion MCP；本期以前端调 **本机 API** 为主，可与脚本行为对齐（如 `replace` 语义）。 |

### 6.1 写入路径与 Page / Database 分型（技术决议 · 已确认）

> **问题**：列表若不区分类型，可能出现「按更新页面正文的方式去写，目标却是 **database 容器**」，导致 API 失败或行为错误。

| 概念 | 说明 |
|------|------|
| **database 容器** | Notion 中的「数据库」对象；**不能**按普通页面正文块整体「覆盖/补充 markdown」同一套逻辑；**新增行**应 `POST /pages` 且 `parent.database_id` + **properties**。 |
| **数据库中的一行** | API 上仍是 **page**（`parent.database_id`）；更新正文/属性用 **page** 相关接口，与容器不同。 |
| **普通 page** | `parent.page_id` 子页面或独立页；正文多用 **blocks** 追加/替换（与现有 `update_page` + `replace` 一致）。 |

| 决议 | 内容 |
|------|------|
| 列表行元数据 | 每条列表项**必须**携带 Notion 返回的 **`object`（page / database）** 及 **`id`**；数据库查询结果均为 `page`（行），**禁止**把 **database 容器 id** 当作「可覆盖正文的 page」进入更新页。 |
| 库内行 | 来自 `databases/query` 的条目**必须**保留 **`parent.database_id`**（或等价字段），以便 **按库 schema 更新 properties**、与「普通页面」写入分支区分。 |
| 级联选中「目录」 | 保留 JSON 中 **`notionObjectType`**；**新增**时：若选中为 **database** → 创建库内新行；若为 **page** → 创建子页面（`parent.page_id`）。 |
| 更新页 | 仅允许 **`object === page`** 的目标进入「覆盖/补充正文」流程；若误选 database 容器，UI **拦截**并提示改选库内行或使用「新增」。 |
| 「全部」合并列表 | 仅来自 **database query**，行天然为 **page**；**不**把 **database 容器**当列表行，从设计上避免「指令写页面却指向库对象」的 API 误用。 |
| 概念澄清 | **不区分 page/database 仅指列表 UI 可同源展示**；**提交层必须分型**，否则会出现对 **库容器** 调 **blocks**、或对 **行** 漏传 **properties** 等失败。 |

---

## 7. 行为偏好页 — 独立执行分支（强制）

当操作目标为 **Notion_Knowledge → 行为偏好（供 Notion AI 参考）** 时（页面 id：`4c207a96-1fd6-42d0-8556-cf2e6f565721`，与级联 JSON 中一致），**必须**遵守：

| 项 | 约定 |
|----|------|
| 权威流程 | `10-Topics/Behavior-Preferences-Sync-Playbook.md` 全文 |
| Cursor 侧档案 | `10-Topics/Cursor-usage-profile-and-templates.md`（§3 第 1–9 节与 Notion 对齐；§6 仅 Cursor） |
| 禁止 | **禁止**对该页做「不比对整块覆盖」式更新；**§2 ↔ Notion 第 4 节** 须 **对比合并**（主本与并集规则见 Playbook §3.1） |
| 章节 | 保持 **1–9 节** 结构对齐；优先 **单侧定稿再镜像** |
| Agent | 侧边栏 Agent 可生成 **分段修改建议或补丁式草稿**；**写入前用户确认**；大改版式走 Playbook **§4 临时模板**路径 |

**研发实现**：在路由层根据选中 `id` 或 URL 命中上述页面时，**分支 UI 文案与写 Notion 前置检查**（例如二次确认 + Playbook 链接触达）。

---

## 8. 操作日志

| 项 | 约定 |
|----|------|
| 持久化 | **必须**写入仓库内约定存储（如 JSONL / SQLite / md），以支持 **跨设备**（随 git 或同步策略走）。 |
| 保留 | 记录 **创建起满 30 天** 清除或归档删除（实现时二选一，需在 README 中写明）。 |
| 展示 | 界面 **仅展示最近 5 条**（建议按时间倒序）；**不等于**只存 5 条。 |
| 字段 | 至少包含：时间、内容标题、所属目录、操作类型、结果（成功/失败，可着色）。 |

---

## 9. 依赖与引用索引

| 资源 | 路径或说明 |
|------|------------|
| 级联数据 | `.cursor/mcp/notion_cascader_options.json` |
| Notion 密钥模板 | `.cursor/mcp/notion.env.example` → 本机 `.cursor/mcp/notion.env`（勿提交） |
| 行为偏好同步 | `10-Topics/Behavior-Preferences-Sync-Playbook.md` |
| Cursor 档案 | `10-Topics/Cursor-usage-profile-and-templates.md` |
| Notion 工作流 | `.cursor/mcp/run_notion_workflow.py`、`NOTION_WORKFLOW_README.md` |
| 统一入口策略 | `10-Topics/Notion-统一入口规范.md`（若与 MCP/插件路由相关） |
| rclone / 同步（后续模块） | `.cursor/tools/cd2_sync_config.cmd` 等（本期仅索引，不实现） |

---

## 10. MVP 交付检查清单（研发自勾）

- [ ] 侧栏 **Notion 作业** 可进入列表 / 新增 / 更新
- [ ] 级联读取 `notion_cascader_options.json`；**全部** = 按 §5.1 仅聚合 JSON 内 **database** 节点
- [ ] 列表：查询、分页、行内查看/更新；**无**首屏全局「更新」按钮；每行保留 **§6.1** 元数据（含库内行的 `database_id`）
- [ ] 本机 API 读 `.cursor/mcp/notion.env`；前端不携带 Token
- [ ] 新增 / 更新：**手动提交**；Agent 仅侧边栏 + 指令回写
- [ ] **行为偏好页** 命中 Playbook 分支与防误覆盖提示
- [ ] 操作日志：持久化、30 天清理策略、UI 仅 5 条
- [ ] README 或本文件 §11 记录：如何刷新级联 JSON、如何配置 Notion Token

---

## 11. 环境与密钥（执行时补全）

- Notion Token：`.cursor/mcp/notion.env`（`NOTION_TOKEN`）— **勿提交密钥**；文档与示例文件仅写变量名与占位。
- **换机最小步骤（自用）**：克隆/同步仓库 → 复制 `.cursor/mcp/notion.env.example` 为 `.cursor/mcp/notion.env` 并填入 Token → 安装前端与后端依赖 → 启动本机 API 与前端（具体命令见模块 README）。
- **首期运行方式**：`npm` / `python` 版本要求由研发在 Plan 阶段写入 `20-Projects/Cursor-Workspace/`（或选定目录）中的 README。

---

## 12. 修订记录

| 日期 | 说明 |
|------|------|
| 2026-05-01 | 初版：汇总 Notion 作业 MVP、Agent 约定、级联与「全部」、日志、行为偏好分支 |
| 2026-05-01 | Plan 迭代：§3.1 多设备自用架构（本机 API + Vite 优先）；§5.1「全部」仅 JSON 内 database 聚合；§6.1 写入按 page/database/行分型，避免对库容器当正文更新 |
| 2026-05-01 | 合并 Ask 结论：§3.1 补充「不推荐纯前端直连」、`notion.env.example`；§5.1 强调列表行保留 `database_id`；§6.1 补充库内行 properties、UI 与提交层分型说明；§11 换机步骤 |
| 2026-05-01 | 头部增加指向 Plan 任务列表与续跑约定 |

---

*执行前在 Plan 模式将 §10 拆为迭代任务与依赖顺序；与 Notion 写入相关的任务须带 **dry-run / 确认** 与安全开关说明。*
