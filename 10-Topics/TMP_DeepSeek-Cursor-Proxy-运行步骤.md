---
Lifecycle: 临时
title: DeepSeek Cursor 中间件——换机与日常使用（仅「须重做」步骤）
---

# DeepSeek Cursor 中间件：须重做步骤清单

中间件仓库：[deepseek-cursor-proxy](https://github.com/yxlao/deepseek-cursor-proxy)。  
作用简述：补全 Cursor 与 DeepSeek 思考模式工具调用所需的 `reasoning_content`；配合 **ngrok** 提供 Cursor 可用的 **HTTPS Base URL**（通常不能用纯 `localhost`）。

下文 **只保留换电脑后要重来、以及每次开聊前要做的步骤**；随移动硬盘已有的源码、已申请的 DeepSeek Key 等「不必因换机重复做的事」合并写在文末对照，不占操作清单。

---

## 一、换一台电脑（或新 Windows 用户）之后：按顺序做

以下 **每台曾用来「本机跑代理 + ngrok」的电脑各做一遍**（同一台电脑只需做一次，除非重装系统 / 换新用户配置）。

1. **安装 Python 3.10+**（若该机尚未安装），并保证终端里能执行 `python`（或 `py -3`）。
2. **插上移动硬盘**，在 Cursor 中打开 **同一工作区根目录**。中间件源码路径固定为：  
   `_tools/deepseek-cursor-proxy`
3. 在该目录执行 **可编辑安装**（新机上的 Python 库里还没有这条命令）：  
   `pip install -e .`  
   （亦可按上游 README 使用 `uv run` 等等价方式，只要能启动 `deepseek-cursor-proxy`。）
4. **安装 ngrok**，并在该机执行一次：  
   `ngrok config add-authtoken <Authtoken>`  
   （Token 仍用 ngrok 账号里那一个即可；**配置文件写在当前电脑的 `%LOCALAPPDATA%\ngrok`**，不跟硬盘走。）
5. 保证本机终端能运行 **`ngrok`**（加入 PATH，或使用 `ngrok.exe` 全路径——与此前用法一致）。
6. 在 **Cursor** 里为该电脑 **重新配置自定义模型**（设置存在本机，不跟硬盘走）：  
   - **模型名**：`deepseek-v4-pro` 或 `deepseek-v4-flash`  
   - **API Key**：DeepSeek 的 Key（可与旧电脑相同）  
   - **Base URL**：待代理启动后，填本次隧道给出的 **`https://<子域>/v1`**（**末尾必须含 `/v1`**）  
   - 需要时用 **`Ctrl+Shift+0`** 启用自定义 API（以当前 Cursor 版本为准）。

说明：用户目录下的 **`%USERPROFILE%\.deepseek-cursor-proxy\`**（`config.yaml`、SQLite 缓存）也是 **按机器 / 用户生成**的；换机会有新的配置文件，一般 **不必手动拷贝**旧机缓存。

---

## 二、每次打算用 DeepSeek（经本机代理）时：要做

与是否刚换机无关，**只要本次会话要用**，就需要：

1. 在终端执行 **`deepseek-cursor-proxy`**，**保持该窗口不要关**。  
2. 看终端或 [ngrok Dashboard](https://dashboard.ngrok.com) 里的 **当前公网 HTTPS 地址**；若与 Cursor 里不一致（免费隧道常会变），在 Cursor 中 **更新 Base URL** 为 **`…/v1`**。  
3. 在 Cursor 中选对应模型，再对话或开 Agent。

常用调试：`deepseek-cursor-proxy --verbose`。  
不走 ngrok 仅适合允许 localhost 的客户端：`--no-ngrok`（Cursor 常见用法仍依赖隧道）。

---

## 三、换机时一般「不必重做」的对照（仅说明，非操作步骤）

| 项目 | 说明 |
|------|------|
| **再次 git clone 中间件** | 工作区在移动硬盘上且已含 `_tools/deepseek-cursor-proxy` 时，**不必**仅为换机再克隆一份。 |
| **向 DeepSeek 重新申请账号 / Key** | 不必；在同一台新机 Cursor 里 **粘贴已有 Key** 即可（见上文第一节第 6 步）。 |
| **注册第二个 ngrok 账号** | 不必；同一 Authtoken 可在多台电脑分别执行 `config add-authtoken`。 |

---

## 四、排查与参考

- 连不上：核对 **代理是否在跑**、**ngrok 是否在线**、**模型名**、**Base URL 是否含 `/v1`**。  
- **`PermissionError: ... config.yaml`（拒绝访问）**：多为 `%USERPROFILE%\.deepseek-cursor-proxy` 的 NTFS 权限过严、或被管理员身份创建的目录导致当前用户读不了 `config.yaml`。  
  1. 在工作区根打开 PowerShell，执行：  
     `powershell -NoProfile -ExecutionPolicy Bypass -File ".cursor\tools\fix_deepseek_proxy_config_permissions.ps1"`  
     然后重新运行 `deepseek-cursor-proxy`。  
  2. 仍失败时（终端里 `icacls` 也提示「拒绝访问」）：**以管理员身份**打开 CMD 或 PowerShell，先 **`takeown /f "%USERPROFILE%\.deepseek-cursor-proxy" /r /d y`**，再 **`icacls "%USERPROFILE%\.deepseek-cursor-proxy" /grant "此处填 whoami 的完整账户名:(OI)(CI)F" /T`**，然后再运行修复脚本或启动代理。脚本失败时也会打印可复制的一组命令。  
  3. 若脚本将不可读的 `config.yaml` 备份为 `config.yaml.bak_unreadable_*`，按上游 README 重新生成或手动恢复配置（含 API Key 等）。  
- 上游文档：[思考模式与工具调用](https://api-docs.deepseek.com/guides/thinking_mode#tool-calls)
