"""
CursorAdapter — Cursor 平台的 6 接口实现。

设计原则:
    - IModelProvider: 直接使用 core.model_providers 的 Provider（绕过 Cursor 的 Agent 模型限制），
      这样认知管线可以自由选择 DeepSeek/Kimi/Ollama 而非被 Cursor 锁定
    - IRuleEngine: 解析 .cursor/rules/*.mdc 文件，支持 alwaysApply + task_triggers 过滤
    - IToolProvider: 提供文件读写 / 搜索 / Shell 执行的基础工具集
    - IHookBus: 读取 hooks.json，执行钩子命令（subprocess）
    - ISkillLoader: 扫描 .cursor/skills/**/SKILL.md
    - IUserInteraction: CLI input() 模式（Cursor 内仍可用 AskQuestion 工具作为补充）

Usage:
    from adapters.cursor.adapter import CursorAdapter

    adapter = CursorAdapter(project_dir="/path/to/socius")
    rules = adapter.rule_engine.load_rules()
    active = adapter.rule_engine.filter_active(rules, task_context={"task_type": "notion_create"})
"""

from __future__ import annotations

import json as _json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# IModelProvider 实现在 model_providers.py 中
# CursorAdapter 的 model_provider 属性直接返回对应 Provider
# ──────────────────────────────────────────────

# ──────────────────────────────────────────────
# IRuleEngine — .mdc 规则解析
# ──────────────────────────────────────────────


class CursorRuleEngine:
    """解析 .cursor/rules/*.mdc 文件，提取 frontmatter + body。

    Cursor 原生机制:
        - alwaysApply: true → 每条对话自动注入
        - task_triggers: [...] → 任务类型匹配时注入
        - globs: [...] → 匹配文件时注入
    本实现读取并解析所有规则文件，通过 filter_active() 按任务上下文过滤。
    """

    def __init__(self, rules_dir: str):
        self.rules_dir = Path(rules_dir)

    def load_rules(self, rule_dir: str = "") -> list[dict]:
        """加载所有 .mdc 文件。

        Returns:
            [{path, content, frontmatter: dict}] 按文件名排序
        """
        target = Path(rule_dir) if rule_dir else self.rules_dir
        if not target.exists():
            logger.warning("规则目录不存在: %s", target)
            return []

        rules = []
        for f in sorted(target.glob("*.mdc")):
            parsed = self._parse_mdc(f)
            if parsed:
                rules.append(parsed)
        return rules

    def _parse_mdc(self, path: Path) -> dict | None:
        """解析单个 .mdc 文件。

        兼容性处理：
            - 优先 UTF-8（大部分 .mdc 文件的标准编码）
            - 降级 GBK（中文 Windows 编辑器可能用 GBK 保存）
            - 如 UTF-8 仅少量字节损坏（编辑器编码混乱），用 errors="replace" 替换损坏字节
        """
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                try:
                    text = path.read_text(encoding="gbk")
                except Exception:
                    logger.warning("无法读取规则文件（编码错误）: %s", path)
                    return None
        except Exception:
            return None

        fm = {}
        body_start = 0
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                fm_text = parts[1]
                body_start = len(parts[0]) + len(parts[1]) + 6  # "---" x2 + 换行
                for line in fm_text.strip().split("\n"):
                    line = line.strip()
                    if ":" in line:
                        key, _, value = line.partition(":")
                        key = key.strip()
                        value = value.strip()
                        # 尝试解析为 JSON/列表
                        parsed_val = self._coerce_value(value)
                        fm[key] = parsed_val

        body = text[body_start:].strip()
        return {
            "path": str(path),
            "filename": path.name,
            "frontmatter": fm,
            "body": body,
        }

    @staticmethod
    def _coerce_value(value: str) -> Any:
        """将 frontmatter 值转为合适的 Python 类型."""
        v = value.strip()
        if v.lower() == "true":
            return True
        if v.lower() == "false":
            return False
        if v.startswith("[") and v.endswith("]"):
            try:
                return _json.loads(v)
            except (_json.JSONDecodeError, ValueError):
                pass
        return v

    def filter_active(
        self, rules: list[dict], /, *, task_context: dict | None = None
    ) -> list[dict]:
        """根据任务上下文过滤当前应激活的规则。

        过滤逻辑:
            1. alwaysApply: true → 始终激活
            2. task_triggers 匹配 task_context["task_type"] → 激活
            3. globs 无匹配逻辑（Cursor 自动处理，此处跳过）
            4. 前两条都不满足 → 休眠

        Args:
            rules: load_rules() 的输出
            task_context: {task_type: str, domain: str, risk_level: str}

        Returns:
            应激活的规则子集（保留原结构）
        """
        active = []
        task_type = (task_context or {}).get("task_type", "")

        for rule in rules:
            fm = rule.get("frontmatter", {})

            # 条件 1: alwaysApply
            if fm.get("alwaysApply"):
                active.append(rule)
                continue

            # 条件 2: task_triggers 匹配
            triggers = fm.get("task_triggers", [])
            if isinstance(triggers, list) and task_type:
                if task_type in triggers:
                    active.append(rule)
                    continue

            # 条件 3: 无匹配 → 休眠（不注入上下文）
            logger.debug("规则休眠: %s", rule.get("filename"))

        return active

    def format_for_context(self, rules: list[dict]) -> str:
        """将激活规则格式化为可注入 Agent 上下文的文本。

        格式与 Cursor alwaysApply 注入格式一致::
            ---
            description: ...
            ---
            # 规则标题
            规则正文...
        """
        parts = []
        for rule in rules:
            fm = rule.get("frontmatter", {})
            desc = fm.get("description", rule.get("filename", ""))
            parts.append(f"---\ndescription: {desc}\n---\n\n{rule.get('body', '')}")
        return "\n\n".join(parts)


# ──────────────────────────────────────────────
# IToolProvider — 基础工具集
# ──────────────────────────────────────────────


class CursorToolProvider:
    """基础文件 + Shell 工具提供者。

    Cursor 原生工具（Read/Write/Shell/Grep/Glob/AskQuestion）由平台自动注入。
    本实现为独立运行场景提供备选路径。

    工具列表:
        - read: 读取文件
        - write: 写入文件
        - shell: 执行命令
        - grep: 文本搜索（rg）
        - glob: 文件匹配
        - delete: 删除文件
    """

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)

    def execute(self, tool_name: str, /, **params) -> dict:
        """执行工具调用。

        Returns:
            {success: bool, output: str, error: str|None}
        """
        try:
            if tool_name == "read":
                return self._read(params)
            elif tool_name == "write":
                return self._write(params)
            elif tool_name == "shell":
                return self._shell(params)
            elif tool_name == "grep":
                return self._grep(params)
            elif tool_name == "glob":
                return self._glob(params)
            elif tool_name == "delete":
                return self._delete(params)
            else:
                return {"success": False, "output": "", "error": f"未知工具: {tool_name}"}
        except Exception as e:
            return {"success": False, "output": "", "error": f"{type(e).__name__}: {e}"}

    def list_tools(self) -> list[str]:
        return ["read", "write", "shell", "grep", "glob", "delete"]

    def _read(self, params: dict) -> dict:
        path = Path(params.get("path", ""))
        if not path.is_absolute():
            path = self.project_dir / path
        if not path.exists():
            return {"success": False, "output": "", "error": f"文件不存在: {path}"}
        content = path.read_text(encoding="utf-8")
        offset = params.get("offset", 0)
        limit = params.get("limit")
        lines = content.split("\n")
        if limit:
            lines = lines[offset : offset + limit]
        elif offset > 0:
            lines = lines[offset:]
        return {"success": True, "output": "\n".join(lines), "error": None}

    def _write(self, params: dict) -> dict:
        path = Path(params.get("path", ""))
        if not path.is_absolute():
            path = self.project_dir / path
        contents = params.get("contents", "")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
        return {"success": True, "output": f"已写入: {path}", "error": None}

    def _shell(self, params: dict) -> dict:
        command = params.get("command", "")
        cwd = params.get("working_directory")
        if cwd:
            cwd = str(Path(cwd))
        timeout = params.get("block_until_ms", 30000) / 1000.0
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout,
            )
            output = result.stdout
            if result.stderr:
                output += "\n[stderr]\n" + result.stderr
            return {
                "success": result.returncode == 0,
                "output": output.strip(),
                "exit_code": result.returncode,
                "error": None if result.returncode == 0 else f"exit_code={result.returncode}",
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "output": "", "error": f"超时 ({timeout}s)"}

    def _grep(self, params: dict) -> dict:
        pattern = params.get("pattern", "")
        path = params.get("path")
        if not path:
            path = str(self.project_dir)
        try:
            result = subprocess.run(
                ["rg", "--no-heading", "-n", pattern, path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return {"success": True, "output": result.stdout.strip(), "error": None}
        except FileNotFoundError:
            return {"success": False, "output": "", "error": "rg 未安装"}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}

    def _glob(self, params: dict) -> dict:
        pattern = params.get("glob_pattern", "**/*")
        target = Path(params.get("target_directory", str(self.project_dir)))
        matches = sorted(str(p) for p in target.glob(pattern))
        return {"success": True, "output": "\n".join(matches), "error": None}

    def _delete(self, params: dict) -> dict:
        path = Path(params.get("path", ""))
        if not path.is_absolute():
            path = self.project_dir / path
        if not path.exists():
            return {"success": False, "output": "", "error": f"文件不存在: {path}"}
        try:
            if path.is_dir():
                import shutil
                shutil.rmtree(path)
            else:
                path.unlink()
            return {"success": True, "output": f"已删除: {path}", "error": None}
        except Exception as e:
            return {"success": False, "output": "", "error": str(e)}


# ──────────────────────────────────────────────
# IHookBus — 钩子事件总线
# ──────────────────────────────────────────────


class CursorHookBus:
    """读取 .cursor/hooks.json，执行钩子命令。

    Cursor 原生机制:
        - sessionStart → 对话开始时触发
        - postToolUseFailure → 工具调用失败时触发
        - afterShellExecution → Shell 执行后触发
        - beforeMCPExecution → MCP 调用前触发
    """

    def __init__(self, hooks_file: str):
        self.hooks_file = Path(hooks_file).resolve()
        self._hooks: dict[str, list[dict]] = {}

        if self.hooks_file.is_file():
            try:
                data = _json.loads(self.hooks_file.read_text(encoding="utf-8"))
                self._hooks = data.get("hooks", {})
            except UnicodeError:
                try:
                    data = _json.loads(self.hooks_file.read_text(encoding="utf-8", errors="replace"))
                    self._hooks = data.get("hooks", {})
                except Exception:
                    logger.exception("hooks.json 解析失败")
            except Exception:
                logger.exception("hooks.json 解析失败")

    def fire(self, event_name: str, /, **payload) -> dict:
        """触发事件，执行所有已注册的钩子。

        Returns:
            {success: bool, results: [{hook_name, exit_code, stdout, stderr}]}
        """
        commands = self._hooks.get(event_name, [])
        if not commands:
            return {"success": True, "results": []}

        results = []
        for entry in commands:
            cmd = entry.get("command", "")
            if not cmd:
                continue
            try:
                proc = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                results.append({
                    "command": cmd,
                    "exit_code": proc.returncode,
                    "stdout": proc.stdout.strip(),
                    "stderr": proc.stderr.strip(),
                })
            except subprocess.TimeoutExpired:
                results.append({
                    "command": cmd,
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": "timeout",
                })
            except Exception as e:
                results.append({
                    "command": cmd,
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": str(e),
                })

        all_ok = all(r["exit_code"] == 0 for r in results)
        return {"success": all_ok, "results": results}

    def register(self, event_name: str, command: str) -> None:
        """运行时注册钩子（不持久化到 hooks.json）。"""
        if event_name not in self._hooks:
            self._hooks[event_name] = []
        self._hooks[event_name].append({"command": command})


# ──────────────────────────────────────────────
# ISkillLoader — 技能发现
# ──────────────────────────────────────────────


class CursorSkillLoader:
    """扫描 .cursor/skills/**/SKILL.md 文件。

    Cursor 原生机制:
        所有 SKILL.md 文件在对话开始时自动注入到 Agent 上下文。
        本实现手动扫描并解析，供框架层按需加载。
    """

    def __init__(self, skills_dir: str):
        self.skills_dir = Path(skills_dir)

    def discover(self, skill_dir: str = "") -> list[dict]:
        """扫描技能目录，返回所有技能。

        Returns:
            [{name, display_name, path, frontmatter: dict, body: str}]
        """
        target = Path(skill_dir) if skill_dir else self.skills_dir
        if not target.exists():
            return []

        skills = []
        for skill_file in sorted(target.rglob("SKILL.md")):
            parsed = self._parse_skill(skill_file)
            if parsed:
                skills.append(parsed)
        return skills

    def _parse_skill(self, path: Path) -> dict | None:
        """解析单个 SKILL.md。"""
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return None

        fm = {}
        body_start = 0
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                fm_text = parts[1]
                body_start = len(parts[0]) + len(parts[1]) + 6
                for line in fm_text.strip().split("\n"):
                    line = line.strip()
                    if ":" in line:
                        key, _, value = line.partition(":")
                        key = key.strip()
                        value = value.strip()
                        if value.lower() == "true":
                            value = True  # type: ignore[assignment]
                        elif value.lower() == "false":
                            value = False  # type: ignore[assignment]
                        fm[key] = value

        body = text[body_start:].strip()
        name = path.parent.name if path.parent.name != "skills" else path.stem

        return {
            "name": name,
            "display_name": fm.get("name", fm.get("title", name)),
            "description": fm.get("description", ""),
            "path": str(path),
            "frontmatter": fm,
            "body": body,
        }

    def inject(self, skills: list[dict], /) -> str:
        """格式化为可注入上下文的技能清单。

        Format::
            <available_skills>
            <agent_skill fullPath="...">描述文本</agent_skill>
            </available_skills>
        """
        if not skills:
            return ""

        lines = ["<available_skills>"]
        lines.append("描述文本: 当用户要求执行任务时，检查以下可用技能是否能帮助完成任务。")
        for sk in skills:
            desc = sk.get("description", sk.get("name", ""))
            full_path = sk.get("path", "")
            lines.append(f'<agent_skill fullPath="{full_path}">{desc}</agent_skill>')
        lines.append("</available_skills>")
        return "\n".join(lines)


# ──────────────────────────────────────────────
# IUserInteraction — 用户交互
# ──────────────────────────────────────────────


class CursorUserInteraction:
    """用户交互实现。CLI input() 作为后备方案。

    Cursor 原生使用 AskQuestion 工具（结构化多选面板）。
    独立运行场景下使用 sys.stdin.readline() 交互。
    """

    @staticmethod
    def ask(title: str, /, *, questions: list[dict]) -> list[dict]:
        """向用户展示问题并获取回答（CLI 模式）。

        Args:
            title: 问题面板标题
            questions:
                [{id, prompt, options: [{id, label}], allow_multiple: bool}]

        Returns:
            [{question_id, selected: [option_id]}]
        """
        print(f"\n{'=' * 60}")
        print(f"  {title}")
        print(f"{'=' * 60}")

        answers = []
        for q in questions:
            qid = q["id"]
            prompt = q["prompt"]
            options = q.get("options", [])
            allow_multiple = q.get("allow_multiple", False)

            print(f"\n📋 {prompt}")
            for i, opt in enumerate(options, 1):
                print(f"  {i}. {opt['label']}")

            if allow_multiple:
                print("  (多选用逗号分隔，如 1,3)")
            else:
                print("  (请输入数字)")

            try:
                raw = input("> ").strip()
                if allow_multiple:
                    indices = [int(x.strip()) - 1 for x in raw.split(",") if x.strip()]
                else:
                    indices = [int(raw) - 1] if raw.isdigit() else [0]

                selected = [
                    options[i]["id"] for i in indices if 0 <= i < len(options)
                ]
                answers.append({"question_id": qid, "selected": selected})
            except (EOFError, KeyboardInterrupt):
                # 非交互模式：默认选第一项
                answers.append({
                    "question_id": qid,
                    "selected": [options[0]["id"]] if options else [],
                })

        return answers

    @staticmethod
    def notify(message: str, /, *, level: str = "info") -> None:
        """非阻塞通知。"""
        prefix = {"info": "ℹ", "warn": "⚠", "error": "✖"}.get(level, "ℹ")
        print(f"{prefix} {message}")


# ──────────────────────────────────────────────
# CursorAdapter — 组装 6 接口的入口类
# ──────────────────────────────────────────────


class CursorAdapter:
    """Cursor 平台适配器——6 接口的聚合入口。

    Usage::

        adapter = CursorAdapter()
        rules = adapter.rule_engine.load_rules()
        active = adapter.rule_engine.filter_active(rules, task_context={"task_type": "notion_create"})
        adapter.hook_bus.fire("sessionStart")
        skills = adapter.skill_loader.discover()
    """

    def __init__(
        self,
        project_dir: str | None = None,
        *,
        model_name: str = "deepseek-v4-pro",
        api_key: str | None = None,
    ):
        if project_dir is None:
            project_dir = Path.cwd()
        self.project_dir = Path(project_dir)

        # 6 接口实例
        self.rule_engine = CursorRuleEngine(str(self.project_dir / ".cursor" / "rules"))
        self.tool_provider = CursorToolProvider(str(self.project_dir))
        self.hook_bus = CursorHookBus(str(self.project_dir / ".cursor" / "hooks.json"))
        self.skill_loader = CursorSkillLoader(str(self.project_dir / ".cursor" / "skills"))
        self.user_interaction = CursorUserInteraction()

        # IModelProvider: 延迟创建（避免无关场景的 API Key 校验）
        self._model_name = model_name
        self._api_key = api_key
        self._model_provider = None

    @property
    def model_provider(self):
        """惰性创建 IModelProvider。"""
        if self._model_provider is None:
            from core.model_providers import create_provider

            self._model_provider = create_provider(self._model_name, api_key=self._api_key)
        return self._model_provider

    def switch_model(self, model_name: str, *, api_key: str | None = None) -> None:
        """运行时切换模型。"""
        self._model_name = model_name
        self._api_key = api_key
        self._model_provider = None  # 下次访问时重建

    def summary(self) -> dict:
        """返回适配器状态摘要。"""
        rules_count = len(self.rule_engine.load_rules())
        skills_count = len(self.skill_loader.discover())
        hooks_events = list(self.hook_bus._hooks.keys())  # noqa: SLF001
        return {
            "platform": "Cursor",
            "project_dir": str(self.project_dir),
            "model": self._model_name,
            "rules_loaded": rules_count,
            "skills_discovered": skills_count,
            "hook_events": hooks_events,
            "tools": self.tool_provider.list_tools(),
        }
