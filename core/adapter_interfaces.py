"""
Platform Adapter Interfaces — 框架层与平台适配器之间的契约。

框架核心（core/）只依赖这 6 个 Protocol 接口，不直接依赖任何平台 API。
每个目标平台（Cursor / VS Code / Docker / Web IDE）只需实现这些接口即可接入。

Usage::

    from core.adapter_interfaces import IModelProvider

    class MyModelProvider(IModelProvider):
        def complete(self, prompt, /, *, system_prompt=""):
            ...
        def complete_json(self, prompt, /, *, schema=None):
            ...

Design Principle:
    接口只定义认知管线需要的最小模型能力。不定义流式输出、不定义 Token 计数、
    不定义多模型路由、不定义 embedding——这些是平台层的事。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


# ──────────────────────────────────────────────
# 1. IModelProvider — 模型推理
# ──────────────────────────────────────────────

@runtime_checkable
class IModelProvider(Protocol):
    """模型推理接口——认知管线调用模型的最小契约。

    设计约束：
        - 同步阻塞：认知管线（分类/提炼/合成）是批处理，不需要流式输出
        - 不定义 Token 计数/成本/路由：这些是平台适配器的实现细节
        - ``complete_json`` 为 schema 驱动的结构化输出场景而设
    """

    def complete(self, prompt: str, /, *, system_prompt: str = "") -> str:
        """单次推理，返回纯文本。

        Args:
            prompt: 用户提示词（必选，positional-only）
            system_prompt: 系统提示词（可选，keyword-only）

        Returns:
            模型生成的完整文本（非流式）

        Example (VS Code adapter)::

            model = await vscode.lm.selectChatModels({family: "gpt-4o"})[0]
            response = await model.sendRequest(messages, {})
            return await response.text()
        """
        ...

    def complete_json(self, prompt: str, /, *, schema: dict | None = None) -> dict:
        """单次推理，返回结构化 JSON。

        Args:
            prompt: 用户提示词
            schema: 可选的 JSON schema 约束。实现层若底层模型不支持
                    JSON mode，可在 system_prompt 中追加
                    "Respond ONLY with valid JSON following: {schema}"
                    并手动 json.loads() 解析

        Returns:
            解析后的 dict

        Example (Ollama adapter)::

            sp = "Respond ONLY with valid JSON."
            if schema:
                sp += f"Schema: {json.dumps(schema)}"
            text = self.complete(prompt, system_prompt=sp)
            return json.loads(text)
        """
        ...


# ──────────────────────────────────────────────
# 2. IRuleEngine — 规则加载与过滤
# ──────────────────────────────────────────────

@runtime_checkable
class IRuleEngine(Protocol):
    """规则引擎接口——加载 .mdc 规则文件并过滤激活规则。

    当前 Cursor 版本的规则 loader 隐式依赖 Cursor 的 alwaysApply 机制。
    独立平台需自行实现规则发现 + 过滤 + 上下文注入。
    """

    def load_rules(self, rule_dir: str = "") -> list[dict]:
        """加载所有规则文件，返回规则列表。

        Args:
            rule_dir: 规则目录路径。空字符串 = 使用默认路径。

        Returns:
            ``[{path, content, frontmatter, ...}]`` 规则列表。
            每条规则包含 frontmatter 字段
            （alwaysApply, severity, task_triggers 等）和 body 正文。
        """
        ...

    def filter_active(self, rules: list[dict], /, *, task_context: dict | None = None) -> list[dict]:
        """根据任务上下文过滤当前应激活的规则。

        Args:
            rules: load_rules() 的输出
            task_context: 当前任务上下文（task_type, domain, risk_level 等）

        Returns:
            应注入到上下文的规则子集
        """
        ...


# ──────────────────────────────────────────────
# 3. IToolProvider — 工具集提供
# ──────────────────────────────────────────────

@runtime_checkable
class IToolProvider(Protocol):
    """工具提供者接口——封装平台级别的文件读写 / 搜索 / 命令执行。

    当前 Cursor 版本的工具由 Cursor SDK 提供（Read/Write/Shell/Grep 等）。
    独立平台需自行实现并注入到 Agent 运行时。
    """

    def execute(self, tool_name: str, /, **params) -> dict:
        """执行一个工具调用。

        Args:
            tool_name: 工具名（如 "read", "write", "shell", "grep", "glob"）
            **params: 工具参数，因工具而异

        Returns:
            ``{success: bool, output: str|dict, error: str|None}``

        Example::

            tool.execute("read", path="/path/to/file.md")
            → {success: True, output: "file content...", error: None}

            tool.execute("shell", command="echo hello")
            → {success: True, output: "hello\\n", error: None}
        """
        ...

    def list_tools(self) -> list[str]:
        """返回当前平台可用的工具名列表。"""
        ...


# ──────────────────────────────────────────────
# 4. IHookBus — 事件钩子总线
# ──────────────────────────────────────────────

@runtime_checkable
class IHookBus(Protocol):
    """钩子事件总线接口——封装平台级别的事件触发机制。

    当前 Cursor 版本使用 hooks.json 的 sessionStart / postToolUseFailure /
    afterShellExecution / beforeMCPExecution 四事件。
    独立平台需映射到自己的生命周期事件。
    """

    def fire(self, event_name: str, /, **payload) -> dict:
        """触发一个事件，执行所有已注册的钩子。

        Args:
            event_name: 事件名（如 "sessionStart", "afterShellExecution"）
            **payload: 事件负载（如 command, exit_code, error_message）

        Returns:
            ``{success: bool, results: [{hook_name, exit_code, stdout, stderr}]}``
        """
        ...

    def register(self, event_name: str, command: str) -> None:
        """注册一个钩子。

        Args:
            event_name: 事件名
            command: 要执行的命令（shell 命令字符串）
        """
        ...


# ──────────────────────────────────────────────
# 5. ISkillLoader — 技能发现与加载
# ──────────────────────────────────────────────

@runtime_checkable
class ISkillLoader(Protocol):
    """技能加载器接口——发现 SKILL.md 文件并注入到 Agent 上下文。

    当前 Cursor 版本使用 .cursor/skills/ 下的 SKILL.md 文件。
    独立平台需实现自己的技能发现机制（扫描目录 → 解析 frontmatter → 注入）。
    """

    def discover(self, skill_dir: str = "") -> list[dict]:
        """扫描技能目录，返回所有可用技能。

        Args:
            skill_dir: 技能目录路径。空字符串 = 使用默认路径。

        Returns:
            ``[{name, description, path, content, frontmatter}]``
        """
        ...

    def inject(self, skills: list[dict], /) -> str:
        """将技能列表格式化为可注入上下文的一段文本。

        Args:
            skills: discover() 的子集（按任务需求筛选后）

        Returns:
            一段 Markdown 文本，适合注入到 system prompt 的技能列表区
        """
        ...


# ──────────────────────────────────────────────
# 6. IUserInteraction — 用户交互
# ──────────────────────────────────────────────

@runtime_checkable
class IUserInteraction(Protocol):
    """用户交互接口——封装平台级别的确认/选择/输入。

    当前 Cursor 版本使用 AskQuestion 结构化面板。
    独立平台需映射到自己的 UI（CLI inquirer / VS Code QuickPick / Web 面板）。
    """

    def ask(self, title: str, /, *, questions: list[dict]) -> list[dict]:
        """向用户展示结构化问题并获取回答。

        Args:
            title: 问题面板标题
            questions: 问题列表，每个问题：
                ``{id, prompt, options: [{id, label}], allow_multiple: bool}``

        Returns:
            用户回答列表：
            ``[{question_id, selected: [option_id, ...]}]``

        Example (CLI with inquirer)::

            questions = [
                {"id": "action", "prompt": "What to do?",
                 "options": [{"id": "run", "label": "Run"}, {"id": "skip", "label": "Skip"}]}
            ]
            answers = ui.ask("Confirm", questions=questions)
            → [{"question_id": "action", "selected": ["run"]}]
        """
        ...

    def notify(self, message: str, /, *, level: str = "info") -> None:
        """非阻塞通知。

        Args:
            message: 通知文本
            level: "info" | "warn" | "error"
        """
        ...
