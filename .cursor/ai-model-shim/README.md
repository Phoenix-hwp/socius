# AI Model Shim - Cursor 通用代理

支持在 Cursor 中使用 **Kimi K2.6** 和 **DeepSeek V4 Pro**。

---

## 快速开始（30 秒）

```cmd
cd <.cursor/ai-model-shim>     # 进入本目录
bootstrap.cmd                  # 首次使用
auto-switch.cmd                # 日常启动
```

---

## 新设备完整流程

```
Git clone 仓库
→ cd .cursor/ai-model-shim
→ bootstrap.cmd        # 引导：检测环境 → 部署 ngrok → 安装依赖 → 配置 Key
→ auto-switch.cmd      # 选模型 → 复制 URL → 在 Cursor 中填入
```

**U盘/网盘二进制包**：`ngrok.exe` 不上传 Git，从外部介质获取。详见 `README_BINARIES.txt`。

---

## 文件清单

| 文件 | 用途 | Git |
|------|------|:---:|
| `bootstrap.cmd` | 跨路径通用引导（新设备 or 新路径）| ✅ |
| `auto-switch.cmd` | 日常启动/切换 Kimi ↔ DeepSeek | ✅ |
| `server.js` | 核心代理（修复 reasoning_content）| ✅ |
| `config.example.json` | 配置模板 | ✅ |
| `config.json` | API Keys | ❌ |
| `ngrok.exe` | 隧道工具（~20MB）| ❌ |
| `node_modules/` | 依赖（npm install）| ❌ |
| `Multi_Device_Sync_Plan.md` | 多设备同步方案 | ✅ |
| `README_BINARIES.txt` | 二进制包版本说明 | ✅ |

---

## 日常使用

```cmd
auto-switch.cmd
```

| 输入 | 模型 |
|:---:|------|
| `1` | Kimi K2.6 (256K) |
| `2` | DeepSeek V4 Pro (1M) |

启动后复制 Ngrok URL，在 Cursor Settings → Models 中配置。

---

## 路径适配

所有脚本基于自身所在目录运行，**不依赖固定盘符**。复制到任意路径后运行 `bootstrap.cmd` 即可适配。

---

## API Key 获取

- Kimi：https://platform.moonshot.cn
- DeepSeek：https://platform.deepseek.com
