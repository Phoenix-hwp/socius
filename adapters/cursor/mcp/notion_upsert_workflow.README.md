# Notion 幂等写入工作流

> 解决 MCP/脚本写入时的重复创建、空壳页面、断线续传问题。

## 三层架构定位

| 层级 | 文件 | 职责 |
|:---:|:---|:---|
| 第二层（框架）| `mod-notion-crud-framework.mdc` | 阶段 A/B/C 定义 |
| 第三层（工作流）| `notion_upsert_workflow.py` | 幂等写入的具体实现 |
| 配置层 | `notion_workflow.upsert.json` | 用户配置模板 |

## 高内聚松耦合设计

- **复用层**：`notion_sdk/client.py`（不重复实现 HTTP/重试逻辑）
- **独立层**：状态管理（`Daily-Backups/.notion_state/`）与核心逻辑解耦
- **配置驱动**：JSON 配置决定行为，不硬编码业务规则
- **跨设备兼容**：状态目录随仓库同步，相对路径自解析

## 核心特性

### 1. 长文自动识别

触发条件（满足任一）：
- 字符数 > 2000
- Notion blocks > 10

长文自动启用：**断点续传 + 状态持久化**

### 2. 幂等写入（Upsert）

流程：`查重 → 决策 → 执行`

| 场景 | on_conflict 策略 | 行为 |
|:---|:---|:---|
| 标题不存在 | — | 创建新页面 |
| 标题已存在 | `skip` | 跳过，返回现有页 |
| 标题已存在 | `update` | 归档旧内容，写入新内容 |
| 标题已存在 | `append` | 保留旧内容，追加新内容 |

### 3. 断点续传

状态文件：`Daily-Backups/.notion_state/pending_<hash>.json`

```json
{
  "page_id": "...",
  "title": "产品说明书",
  "blocks_total": 134,
  "blocks_written": 67,
  "url": "https://..."
}
```

中断后重跑：自动检测状态 → 续传剩余块 → 完成后清理状态文件

## 使用方式

### 命令行

```bash
cd .cursor/mcp
python notion_upsert_workflow.py --config notion_workflow.upsert.json
```

### 配置文件

```json
{
  "mode": "upsert_page",
  "parent": "notion.dir.product_docs",
  "title": "产品说明书（空模板）",
  "content_file": "template.md",
  "on_conflict": "update",
  "title_prop": "标题"
}
```

### 输出示例

**首次创建**：
```json
{
  "ok": true,
  "result": {
    "action": "created",
    "page_id": "...",
    "url": "https://...",
    "blocks_total": 134,
    "blocks_appended": 134,
    "is_long_content": true
  }
}
```

**重复执行（skip 策略）**：
```json
{
  "ok": true,
  "result": {
    "action": "skipped",
    "page_id": "...",
    "message": "标题 '产品说明书' 已存在，跳过创建"
  }
}
```

**断点续传**：
```json
{
  "ok": true,
  "result": {
    "action": "resumed",
    "page_id": "...",
    "blocks_resumed": 67,
    "message": "断点续传完成"
  }
}
```

## 与现有工具的关系

| 工具 | 适用场景 | 幂等性 |
|:---|:---|:---:|
| MCP `notion-create-pages` | 小条随手记 | ❌ |
| `run_notion_workflow.py` | 中等长度文档 | ⚠️ 基础重试 |
| `notion_upsert_workflow.py` | 长文、重要文档 | ✅ 查重+续传 |

## 与 Notion CRUD 规则的配合

### 自动路由（用户无感知）

当用户在对话中说 **「写入Notion」** 或 **「Notion创建」** 时：

```
gateway-command-router.mdc
    ↓
mod-notion-crud-framework.mdc（阶段 A/B/C）
    ↓
flow-notion-create.mdc 六步流程
    ↓
步骤5「执行与回执」自动判定：
├── 短文（≤2000字符 或 ≤10 blocks）→ MCP 快速写入
└── 长文（>2000字符 或 >10 blocks）→ 自动调用 notion_upsert_workflow.py
```

**用户侧**：无需记新指令，仍说「写入Notion」即可。Agent 内部自动选择最优通道。

### 更新场景同理

当用户说 **「更新Notion」** 时：

```
flow-notion-update.mdc 六步流程
    ↓
步骤6「执行更新」自动判定：
├── 短文 → MCP 优先
└── 长文 → notion_upsert_workflow.py（支持策略1清空重写 / 策略2局部合并）
```

### 状态文件生命周期

```
创建/更新/追加长文
    ↓
写入前：创建状态文件（Daily-Backups/.notion_state/）
    ↓
每批写入后：更新状态（blocks_written 进度）
    ↓
完成：自动清理状态文件
    ↓
中断：状态文件保留，重跑脚本自动续传
```

**跨设备**：`Daily-Backups/.notion_state/` 随仓库 Git 同步。换机后重跑脚本可继续续传。

## 待办（可选增强）

- [ ] 批量去重脚本（清理历史重复记录）
- [ ] 并发归档优化（线程池）
- [ ] 更多 Markdown 语法支持（表格、图片等）
