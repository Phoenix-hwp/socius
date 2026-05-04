# AI Model Shim - 多设备同步方案

> v2.0 | 2026-05-04 | 适用场景：不同电脑、不同路径，通过 Git + U盘/网盘分发

---

## 核心原则

| 组件 | 分发方式 | 说明 |
|------|---------|------|
| **代码**（`.cmd`, `.js`, `.json`, `.md`）| Git 同步（Gitee）| 所有脚本和配置文件模板 |
| **密钥**（`config.json`）| ❌ 不提交 Git | `.gitignore` 已排除；**仓库根** `bootstrap-on-pull.cmd` 从 `config.example.json` 生成占位，再按需填 Key |
| **密钥**（`notion.env`）| ❌ 不提交 Git | `.gitignore` 已排除；`bootstrap-on-pull.cmd` 从 `notion.env.example` 生成占位，本机填 `NOTION_TOKEN` |
| **二进制**（`ngrok.exe`）| U盘/网盘 | 不上传 Git（约 20MB），需要时从外部介质获取 |
| **依赖**（`node_modules/`）| 本地安装 | `npm install` 在本机生成（约 50MB）|
| **会话状态**（`.current_model`）| ❌ 不提交 Git | 仅记录当前设备选择的模型 |

---

## 一次初始化，到新路径即插即用（v2.0）

### 目标

让你在任何设备、任何路径上 **先跑仓库根一条命令**，再进目录完成 Shim 初始化。

### 场景零：刚拉取代码（仓库根，推荐最先执行）

```cmd
cd /d "<你的仓库根目录>"
bootstrap-on-pull.cmd
```

从模板生成 `config.json`、`notion.env` 等本地占位，避免脚本因缺文件无法启动。

### 场景一：新设备 / 新路径

```cmd
# 方式1：直接 cd 到仓库根目录（支持任意盘符和路径）
cd /d "D:\Any\Folder\Cursor_Knowledge"
bootstrap-on-pull.cmd

# 方式2：在资源管理器地址栏直接输入 cmd，然后运行
bootstrap-on-pull.cmd
```

自动完成：
1. 从模板生成占位配置文件
2. 环境检测（Node.js / npm）
3. 引导获取二进制文件（ngrok.exe）
4. 安装 Node.js 依赖（`npm install`）
5. 检测 API Keys（需手动填入 config.json）
6. 显示**绝对路径**，方便你定位文件位置

**路径无关**：无论仓库在哪个盘符或路径（含空格），`bootstrap-on-pull.cmd` 都能自适应。

---

## 文件分类与分发策略

### Git 同步（随仓库分发）

```
.cursor/ai-model-shim/
├── auto-switch.cmd         ← 日常切换启动
├── server.js               ← 核心代理
├── package.json            ← 依赖声明
├── config.example.json     ← 配置模板（不含真实 Key）
├── README.md               ← 完整文档
└── Multi_Device_Sync_Plan.md  ← 多设备同步方案
```

### U盘/网盘分发（不提交 Git）

```
<你的网盘或U盘>/AI_Model_Binaries/
├── ngrok.exe               ← 隧道工具（~20MB）
│   └── 备用下载：https://ngrok.com/download
└── README_BINARIES.txt     ← 版本说明
```

### 本地生成（每台设备独立）

```
<本机路径>/.cursor/ai-model-shim/
├── config.json             ← API Keys（手动填入）
├── node_modules/           ← npm install 生成
├── ai-model-shim.log       ← 运行日志
└── .current_model          ← 当前选择的模型
```

---

## 新设备操作流程

### 第 1 步：克隆仓库到任意路径

```bash
git clone <你的Gitee仓库地址> "<你想要的任意路径>"
cd "<你想要的任意路径>"
```

### 第 2 步：运行引导脚本

```cmd
bootstrap-on-pull.cmd
```

按提示完成：
- 从模板生成占位配置文件
- 检查 Node.js（缺失则引导安装）
- 部署 ngrok.exe（选择从 U盘/网盘拷贝或在线下载）
- 安装 npm 依赖
- 检测 API Keys（需手动填入 config.json）

### 第 3 步：启动使用

```cmd
# 切换到 shim 目录（使用 /d 支持跨盘符）
cd /d "<仓库根目录>\.cursor\ai-model-shim"

# 启动
auto-switch.cmd
```

选模型 → 复制 Ngrok URL → 在 Cursor 中配置。

### Cursor 全局配置（一次性）

**每个模型只需在 Cursor 中添加一次：**

- `kimi-k2.6` → 切换到 Kimi 时，只更新 Base URL
- `deepseek-v4-pro` → 切换到 DeepSeek 时，更新 Base URL + API Key

---

## U盘/网盘二进制包管理

### 推荐结构

```
U盘或网盘:\AI_Model_Binaries\
├── ngrok.exe               ← 当前稳定版本
├── README_BINARIES.txt     ← 版本号 + 下载链接
└── archive\                ← 历史版本备份
    └── ngrok_v3.xx.exe
```

### README_BINARIES.txt 内容

```
AI Model Shim - Binary Packages
================================
ngrok.exe
  Version: 3.x.x
  Size: ~20MB
  Download: https://ngrok.com/download
  Config: ngrok authtoken YOUR_TOKEN

How to use:
  1. Copy ngrok.exe to: <repo>\.cursor\ai-model-shim\
  2. Run: ngrok authtoken YOUR_TOKEN
  3. Ready!
```

---

## 模型配置速查

### Kimi K2.6

| 配置项 | 值 |
|--------|-----|
| Base URL | `https://你的ngrok地址.ngrok-free.app/v1` |
| API Key | Kimi API Key（`sk-` 开头）|
| Model | `kimi-k2.6` |

### DeepSeek V4 Pro

| 配置项 | 值 |
|--------|-----|
| Base URL | `https://你的ngrok地址.ngrok-free.app/v1` |
| API Key | DeepSeek API Key（`sk-` 开头）|
| Model | `deepseek-v4-pro` |

### 关键差异

- Kimi 使用国内域名 `api.moonshot.cn`（自动）
- DeepSeek 使用 `api.deepseek.com`（自动）
- DeepSeek 不支持图片输入（Shim 自动过滤）
- Ngrok URL 每次启动可能变化（免费版限制）

---

## 故障排查

| 问题 | 排查方向 |
|------|---------|
| 401 Unauthorized | 检查 API Key 是否正确、账户余额 |
| 400 invalid_request_error（image_url）| DeepSeek 不支持图片，Shim 应自动过滤；若仍有问题，重启 Shim |
| Node.js 未找到 | 安装 Node.js LTS → 重启终端 → 重新运行 bootstrap-on-pull.cmd |
| Ngrok 启动失败 | 检查 authtoken 配置：`ngrok authtoken YOUR_TOKEN` |
| 路径切换后脚本报错 | 重新运行 `bootstrap-on-pull.cmd`（基于新路径自动适应）|

---

## 日常操作速查

```bash
# 新设备初始化（在仓库根目录运行）
cd /d "<仓库根目录>"
bootstrap-on-pull.cmd

# 启动/切换模型（在 shim 目录运行）
cd /d "<仓库根目录>\.cursor\ai-model-shim"
auto-switch.cmd

# 配置 API Keys
编辑 <仓库根目录>\.cursor\ai-model-shim\config.json
（或运行 bootstrap-on-pull.cmd 重新生成模板）

# 查看帮助
type README.md

# 查看运行状态
curl http://127.0.0.1:8787/healthz
```
