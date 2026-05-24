# 贡献指南

感谢你考虑为 Phoenix 贡献代码！

## 开发环境

```bash
git clone https://github.com/phoenixhwp/phoenix.git
cd phoenix
pip install -e .
```

## 项目结构

```
phoenix/
├── core/           ← 框架层（不要直接依赖平台 API）
├── adapters/       ← 平台适配器
├── protocols/      ← 知识协议（CP-xxx.md）
├── plans/          ← 开发计划
├── scripts/        ← 验证脚本
└── docs/           ← 用户文档
```

## 开发流程

1. **Fork + Branch** — 从 `main` 分支创建功能分支 (`feat/xxx` / `fix/xxx`)
2. **写代码** — 遵循现有代码风格
3. **自检** — 运行验证脚本：

```bash
python scripts/verify_cursor_adapter.py
phoenix verify
```

4. **PR** — 提交 Pull Request，描述改动内容和验证结果

## 编码规范

### 框架层 (`core/`)

- **零平台依赖** — `core/` 中的代码不得 `import` 任何 Cursor/VS Code 等平台的 API
- **接口优先** — 需要外部能力时，通过 `core/adapter_interfaces.py` 的 Protocol 声明接口
- **同步优先** — 认知管线是批处理，不使用 async/await

### 适配器 (`adapters/`)

- 每个平台一个子目录
- 实现 6 个 Protocol 接口
- 提供 `__init__.py` 导出聚合类（如 `CursorAdapter`）

### 协议 (`protocols/`)

- 文件命名 `CP-xxx.md`
- Frontmatter 必含 `Title` / `Lifecycle` / `Created`
- 一协议一概念 — 不混搭多种知识类型

## 提交协议

- 每个 Protocol 文件 (`protocols/CP-xxx.md`) 须符合格式一致性规则
- 数据文件 (`.json` / `.jsonl`) 修改后须通过 schema 验证
- `.md` 文件须声明 `Lifecycle` 字段（`瞬态` / `临时` / `阶段` / `长期`）

## 设计原则

- **单一权威源** — 同一数据只在一处定义
- **JSON 不存长文本** — 超过 50 字的文本外迁到 `.md`
- **可运行时计算的不持久化** — 派生数据不入仓库
