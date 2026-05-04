# AI Model Shim - Cursor 通用代理

支持在 Cursor 中使用 **Kimi K2.6** 和 **DeepSeek V4 Pro**。

---

## 快速开始（30 秒）

**刚 `git clone` / `git pull` 后（仓库根目录）：**

```cmd
bootstrap-on-pull.cmd
```

**配置完成后，进入本目录启动：**

```cmd
cd /d "<仓库根目录>\.cursor\ai-model-shim"
auto-switch.cmd          # 选模型 → 复制 URL → 在 Cursor 中填入
```

或从仓库根目录：

```cmd
cd /d "<仓库根目录>"
cd .cursor\ai-model-shim
auto-switch.cmd
```

---

## 新设备完整流程

```
Git clone 仓库到任意路径 (如 D:\Work\Cursor_Knowledge)
→ cd /d "D:\Work\Cursor_Knowledge"              # 切换到仓库根（/d 支持跨盘符）
→ bootstrap-on-pull.cmd                        # 生成占位文件、检测环境等
→ 手动编辑 .cursor\ai-model-shim\config.json 填入 API Keys
→ cd /d "D:\Work\Cursor_Knowledge\.cursor\ai-model-shim"
→ auto-switch.cmd                              # 选模型 → 复制 URL → 在 Cursor 中填入
```

**U盘/网盘二进制包**：`ngrok.exe` 不上传 Git，从外部介质获取。详见 `README_BINARIES.txt`。

---

## 文件清单

| 文件 | 用途 | Git |
|------|------|:---:|
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

所有脚本基于自身所在目录运行，**不依赖固定盘符**。`bootstrap-on-pull.cmd` 在仓库根目录运行一次即可完成跨路径适配。

---

## API Key 获取

- Kimi：https://platform.moonshot.cn
- DeepSeek：https://platform.deepseek.com
