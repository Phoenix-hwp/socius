"""
上下文构建器 — 替代 Cursor alwaysApply 机制的框架层上下文注入引擎。

Cursor 版本:
    Cursor Agent 运行时自动读取 .cursor/rules/ 中 alwaysApply: true 的 .mdc 规则，
    并将其注入到每条对话的系统提示中。

独立框架版本:
    本模块替代 Cursor 的隐式注入。ContextBuilder 按任务上下文动态组装:
        1. 激活规则（通过 IRuleEngine.filter_active）
        2. 认知引擎本体（classifier / synthesizer 的 system prompt）
        3. 技能清单（通过 ISkillLoader.discover → inject）
        4. 平台能力声明（工具列表、钩子事件）
        5. 强制约束前缀（Guard 安全规则）


Usage::

    from core.context_builder import ContextBuilder

    builder = ContextBuilder(
        rule_engine=adapter.rule_engine,
        skill_loader=adapter.skill_loader,
        project_dir="/path/to/project",
    )

    context = builder.build(
        task_context={"task_type": "notion_create", "domain": "notion"},
        mode="interactive",
    )
    # 将 context 注入到 system prompt 的开头
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.adapter_interfaces import IRuleEngine, ISkillLoader

logger = logging.getLogger(__name__)


class ContextBuilder:
    """动态上下文组装器。

    核心职责:
        - 按任务上下文过滤规则（alwaysApply + task_triggers）
        - 格式化为可注入 Agent 的上下文块
        - 处理规则间依赖和排序

    Cursor 依赖解耦:
        当前 Cursor 版本由平台自动注入 alwaysApply 规则。
        独立运行时，本模块接管注入——由框架层显式调用 build()
        并将结果注入到调用 IModelProvider 时的 system_prompt 中。
    """

    # ── 规则优先级映射（影响排序） ──

    PRIORITY_MAP = {
        "gateway": 0,     # 网线路由 → 最先
        "flow-high": 1,   # 高风险安全
        "script": 2,      # 编码约束
        "data": 3,        # 数据治理
        "external": 4,    # 外部依赖边界
        "git": 5,         # Git 安全
        "impact": 6,      # 变更影响枚举
        "edit-brief": 7,  # 脚本修改预告
        "mod": 10,        # 模块规则（通用）
        "flow": 11,       # 流规则（具体场景）
        "default": 99,    # 其他 — 最后
    }

    def __init__(
        self,
        rule_engine: IRuleEngine,
        skill_loader: ISkillLoader | None = None,
        *,
        project_dir: str = ".",
    ):
        self.rule_engine = rule_engine
        self.skill_loader = skill_loader
        self.project_dir = project_dir

        # 缓存
        self._all_rules: list[dict] | None = None

    # ──────────────────────────────────────────
    # 公开 API
    # ──────────────────────────────────────────

    def build(
        self,
        *,
        task_context: dict | None = None,
        include_skills: bool = True,
        mode: str = "interactive",
    ) -> str:
        """组装完整的 Agent 上下文。

        Args:
            task_context: 任务上下文 {task_type, domain, risk_level}
            include_skills: 是否注入技能清单
            mode: "interactive"（对话）| "batch"（批处理认知管线）| "guard"（Guard 安全闸）

        Returns:
            格式化的上下文字符串，可直接注入到 system_prompt
        """
        sections = []

        # 1. 强制约束前缀（Guard 安全规则 — 全模式注入）
        guard_rules = self._get_guard_rules()
        if guard_rules:
            sections.append(self._format_guard_section(guard_rules))

        # 2. 激活的任务规则
        active_rules = self._get_active_rules(task_context)
        if active_rules:
            sections.append(
                self.rule_engine.format_for_context(active_rules)  # type: ignore[union-attr]
            )

        # 3. 技能清单（仅交互模式）
        if include_skills and self.skill_loader and mode == "interactive":
            skills = self.skill_loader.discover()
            if skills:
                sections.append(self.skill_loader.inject(skills))

        # 4. 任务类型感知 — 注入 task_type 标签
        if task_context:
            sections.append(self._format_task_context(task_context))

        return "\n\n".join(filter(None, sections))

    def build_guard_context(self) -> str:
        """Guard 安全闸门专用上下文 — 只注入高风险安全规则。"""
        guard_rules = self._get_guard_rules()
        if not guard_rules:
            return ""

        return "\n\n".join(
            self.rule_engine.format_for_context([r])
            for r in guard_rules
        )

    # ──────────────────────────────────────────
    # 内部方法
    # ──────────────────────────────────────────

    def _get_all_rules(self) -> list[dict]:
        """惰性加载全部规则。"""
        if self._all_rules is None:
            self._all_rules = self.rule_engine.load_rules()
        return self._all_rules

    def _get_active_rules(self, task_context: dict | None) -> list[dict]:
        """按 alwaysApply + task_triggers 过滤激活规则。"""
        all_rules = self._get_all_rules()
        if not task_context:
            # 无任务上下文 → 只激活 alwaysApply 规则
            return [r for r in all_rules if r.get("frontmatter", {}).get("alwaysApply")]

        return self.rule_engine.filter_active(all_rules, task_context=task_context)

    def _get_guard_rules(self) -> list[dict]:
        """获取高风险安全相关规则（全模式强制注入）。

        匹配规则文件名中的关键词:
            - high-risk-safety → 高风险操作防护
            - data-governance → 数据治理宪法
            - git-cross-device → 跨设备路径 + 密钥安全
        """
        all_rules = self._get_all_rules()
        guard_keywords = ["high-risk-safety", "data-governance", "git-cross-device"]
        return [
            r for r in all_rules
            if any(kw in r.get("filename", "") for kw in guard_keywords)
        ]

    def _sort_rules(self, rules: list[dict]) -> list[dict]:
        """按优先级排序规则。"""
        def _priority(rule: dict) -> int:
            filename = rule.get("filename", "")
            for key, pri in self.PRIORITY_MAP.items():
                if key in filename:
                    return pri
            return self.PRIORITY_MAP["default"]
        return sorted(rules, key=_priority)

    @staticmethod
    def _format_guard_section(guard_rules: list[dict]) -> str:
        """格式化 Guard 安全规则为强制前缀块。

        Format::
            <!-- GUARD_MANDATORY_PREFIX -->
            # 🔒 强制安全规则（Guard 注入）
            ...
            <!-- /GUARD_MANDATORY_PREFIX -->
        """
        bodies = []
        for rule in guard_rules:
            bodies.append(rule.get("body", ""))
        content = "\n\n---\n\n".join(bodies)
        return (
            "<!-- GUARD_MANDATORY_PREFIX -->\n"
            "# 🔒 强制安全规则（Guard 注入）\n\n"
            f"{content}\n"
            "<!-- /GUARD_MANDATORY_PREFIX -->"
        )

    @staticmethod
    def _format_task_context(task_context: dict) -> str:
        """格式化为任务类型标签，供 Agent 感知当前任务域。"""
        parts = []
        if task_context.get("task_type"):
            parts.append(f"task_type: {task_context['task_type']}")
        if task_context.get("domain"):
            parts.append(f"domain: {task_context['domain']}")
        if task_context.get("risk_level"):
            parts.append(f"risk_level: {task_context['risk_level']}")

        if not parts:
            return ""

        return (
            "<!-- TASK_CONTEXT_TAGS -->\n"
            f"当前任务上下文: {' | '.join(parts)}\n"
            "<!-- /TASK_CONTEXT_TAGS -->"
        )
