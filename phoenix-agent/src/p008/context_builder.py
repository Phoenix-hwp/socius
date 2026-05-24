"""Injection Engine — three LLM call-point context builders.

Guard MVP v0.2. Constructs structured context for three LLM injection points:

    LLM#1 (Intent)     : task classification → alias table + task-type defs + output_schema
    LLM#2 (Decompose)  : task decomposition + KB framework mounting + anti-bias
    LLM#3 (Fill)       : information completion + slot constraints

Design principles (Issue 5: planning fallacy; Issue 8: availability heuristic):
    - LLM#2 injects duration estimation based on Decision-Log 80th percentile
    - LLM#2 applies KB anti-bias: if ≥2 of top-3 KB results are from last round's
      active protocols → downweight ×0.7 + inject counter-thinking directive
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import statistics


# ── InjectionContext ───────────────────────────────────────────────

@dataclass
class InjectionContext:
    """Complete context bundle to inject into an LLM call point."""

    call_point: str                       # "LLM#1" | "LLM#2" | "LLM#3"
    system_prompt: str = ""
    task_template: str = ""
    kb_frameworks: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    output_schema: Optional[dict] = None
    anti_bias_directives: list[str] = field(default_factory=list)
    duration_guidance: str = ""

    def to_prompt_dict(self) -> dict:
        """Convert to a dict compatible with LLM prompt format."""
        result = {
            "system": self.system_prompt,
            "task": self.task_template,
        }
        if self.constraints:
            result["constraints"] = self.constraints
        if self.kb_frameworks:
            result["kb_frameworks"] = self.kb_frameworks
        if self.output_schema:
            result["output_schema"] = self.output_schema
        if self.anti_bias_directives:
            result["anti_bias"] = self.anti_bias_directives
        if self.duration_guidance:
            result["duration_guidance"] = self.duration_guidance
        return result


# ── Template Registry ──────────────────────────────────────────────

@dataclass
class TaskTemplate:
    """A registered task template for injection."""

    template_id: str
    task_type: str                       # "notion_create" | "code_generate" | "kb_search" | etc.
    description: str = ""
    framework_id: str = ""               # linked KB protocol ID (e.g. "CP-020")
    required_capabilities: list[str] = field(default_factory=list)
    output_medium: str = "text"
    default_output_schema: Optional[dict] = None


class TemplateRegistry:
    """Registry of task templates available for injection into LLM prompts.

    Each template maps a task_type to a framework, capabilities, and output schema.
    At injection time, the context builder queries this registry to attach the
    right template to the LLM prompt.
    """

    def __init__(self) -> None:
        self._templates: dict[str, TaskTemplate] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register built-in task templates."""
        defaults = [
            TaskTemplate(
                "tpl_notion_create",
                "notion_create",
                "Create a Notion page or database row",
                "CP-020",
                ["notion_api", "markdown_render"],
                "notion",
            ),
            TaskTemplate(
                "tpl_notion_query",
                "notion_query",
                "Query/search Notion pages",
                "CP-057",
                ["notion_api", "semantic_search"],
                "notion",
            ),
            TaskTemplate(
                "tpl_notion_update",
                "notion_update",
                "Update existing Notion page content",
                "CP-058",
                ["notion_api", "markdown_render"],
                "notion",
            ),
            TaskTemplate(
                "tpl_notion_delete",
                "notion_delete",
                "Delete/archive a Notion page",
                "CP-059",
                ["notion_api"],
                "notion",
            ),
            TaskTemplate(
                "tpl_code_generate",
                "code_generate",
                "Generate or modify code files",
                "",
                ["file_write", "linter"],
                "file",
            ),
            TaskTemplate(
                "tpl_kb_search",
                "kb_search",
                "Search knowledge base and synthesize answer",
                "",
                ["semantic_search"],
                "text",
            ),
            TaskTemplate(
                "tpl_knowledge_digest",
                "knowledge_digestion",
                "Digest new knowledge into KB protocols",
                "CP-001",
                ["md_parse", "file_write"],
                "file",
            ),
            TaskTemplate(
                "tpl_simulation",
                "simulation",
                "Execute a simulation scenario in sandbox",
                "",
                ["sandbox", "logging"],
                "text",
            ),
            TaskTemplate(
                "tpl_system_audit",
                "system_audit",
                "Full-system architecture/data/code/skills health scan",
                "",
                ["file_scan", "json_parse"],
                "text",
            ),
            TaskTemplate(
                "tpl_conversation",
                "conversation_management",
                "Manage multi-round conversation state",
                "",
                ["text_render"],
                "text",
            ),
        ]
        for tpl in defaults:
            self._templates[tpl.template_id] = tpl

    def get(self, template_id: str) -> Optional[TaskTemplate]:
        return self._templates.get(template_id)

    def get_by_task_type(self, task_type: str) -> Optional[TaskTemplate]:
        """Find the first template matching a given task_type."""
        for tpl in self._templates.values():
            if tpl.task_type == task_type:
                return tpl
        return None

    def register(self, template: TaskTemplate) -> None:
        self._templates[template.template_id] = template

    def list_all(self) -> list[TaskTemplate]:
        return list(self._templates.values())


# ── Duration Estimator ─────────────────────────────────────────────

def estimate_duration(
    task_type: str,
    decision_log_path: Path | None = None,
    default_seconds: int = 600,
) -> tuple[int, str]:
    """Estimate expected duration for a task type based on historical data.

    Issue 5: Planning Fallacy — uses Decision-Log 80th percentile as benchmark.
    If no history, flags ±50% uncertainty.

    Args:
        task_type: The task type to estimate for.
        decision_log_path: Path to Decision-Log.jsonl (optional).
        default_seconds: Default estimate if no history available.

    Returns:
        (estimated_seconds, guidance_string)
    """
    durations = _load_historical_durations(decision_log_path, task_type)

    if not durations:
        low = int(default_seconds * 0.5)
        high = int(default_seconds * 1.5)
        guidance = (
            f"No historical data for task_type '{task_type}'. "
            f"Default estimate: {default_seconds}s (±50%: {low}s–{high}s). "
            f"Adjust by ×1.5 for planning fallacy buffer."
        )
        return (default_seconds, guidance)

    # Use 80th percentile (P80) — accounts for right-skewed duration distributions
    durations.sort()
    p80_idx = int(len(durations) * 0.8)
    p80 = durations[min(p80_idx, len(durations) - 1)]
    median = statistics.median(durations)

    guidance = (
        f"Based on {len(durations)} past executions of '{task_type}': "
        f"median={median}s, P80={p80}s. Use P80 ({p80}s) as estimate. "
        f"Planning fallacy buffer: if estimate feels tight, multiply by ×1.3."
    )
    return (p80, guidance)


def _load_historical_durations(
    log_path: Path | None,
    task_type: str,
) -> list[int]:
    """Load historical durations (in seconds) for a task type from Decision-Log."""
    durations: list[int] = []

    if log_path is None:
        return durations

    if not log_path.exists():
        return durations

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("task_type") != task_type:
                    continue
                dur = entry.get("actual_duration_s") or entry.get("duration_s")
                if isinstance(dur, (int, float)):
                    durations.append(int(dur))
    except Exception:
        pass

    return durations


# ── KB Anti-Bias Engine ────────────────────────────────────────────

def compute_anti_bias_directives(
    current_kb_top_results: list[str],       # e.g. ["CP-020", "CP-057", "CP-098"]
    last_round_active_protocols: list[str],  # e.g. ["CP-020", "CP-057"]
    threshold: int = 2,
    downweight_factor: float = 0.7,
) -> dict:
    """Detect availability heuristic and inject counter-thinking directives.

    Issue 8: Availability Heuristic — when ≥threshold of KB top results are
    from last round's already-activated protocols, the KB retrieval is biased
    toward recently seen content. Inject:
        - Downweight flag for re-ranking
        - Counter-thinking directive for the LLM

    Args:
        current_kb_top_results: Top-N KB protocol IDs from current search.
        last_round_active_protocols: Protocol IDs active in previous round.
        threshold: How many overlaps trigger anti-bias (default 2).
        downweight_factor: Multiplier for ranking score of overlapped protocols.

    Returns:
        {
            "biased": True/False,
            "overlapped_protocols": [...],
            "downweighted": {...},   # protocol_id → factor
            "directives": [...],     # strings to inject into LLM prompt
        }
    """
    overlapped = [pid for pid in current_kb_top_results if pid in last_round_active_protocols]
    biased = len(overlapped) >= threshold

    downweighted = {pid: downweight_factor for pid in overlapped} if biased else {}

    directives = []
    if biased:
        directives.append(
            f"【反置思考】KB检索结果前{len(current_kb_top_results)}项中有{len(overlapped)}项"
            f"来自上一轮已激活协议（{', '.join(overlapped)}）。为避免可得性启发偏差，"
            f"请思考：除了上述框架，是否有更适合当前任务的替代框架？"
            f"已激活协议的检索权重自动降至 ×{downweight_factor}。"
        )

    return {
        "biased": biased,
        "overlapped_protocols": overlapped,
        "downweighted": downweighted,
        "directives": directives,
    }


# ── System Goal (P042) ────────────────────────────────────────────

SYSTEM_GOAL = (
    "SYSTEM_DIRECTIVE: Phoenix 系统的目标是：作为用户的执行搭档（Agent），而非辅助工具（Copilot）。\n"
    "默认自决策、自执行（L0/L1），仅在无经验或高风险时寻求人的判断。\n"
    "人的角色是方向制定者，不是流水线上的审批节点。\n\n"
    "当两个目标冲突时（如效率 vs 安全），按以下优先级裁决：\n"
    "  1. 安全（不可逆损害预防）\n"
    "  2. 一致性（数据质量）\n"
    "  3. 效率（执行速度）\n\n"
    "核心能力：决策（P008）+ 风控（SafetyGate）+ 执行调度（Skills/MCP/API）+ 经验与知识反哺。\n"
    "工具是手脚（可替换），脑子（思考框架/方法论/经验）是核心——能做好决策、选择合适工具、\n"
    "判断执行结果并从中学习，才是 Phoenix 的核心战斗力。"
)


# ── Context Builder ────────────────────────────────────────────────

class ContextBuilder:
    """Build injection contexts for the three LLM call points.

    Usage:
        builder = ContextBuilder()
        ctx = builder.build_intent("notion_create")
        prompt_dict = ctx.to_prompt_dict()
    """

    def __init__(
        self,
        template_registry: Optional[TemplateRegistry] = None,
        decision_log_path: Optional[Path] = None,
    ) -> None:
        self.templates = template_registry or TemplateRegistry()
        self.decision_log_path = decision_log_path

    # ── LLM#1: Intent classification ─────────────────────────

    def build_intent_context(
        self,
        task_type: str,
        alias_map: Optional[dict[str, str]] = None,
        extra_constraints: Optional[list[str]] = None,
    ) -> InjectionContext:
        """Build context for LLM#1 — task classification.

        Injects: alias table, task-type definitions, output_schema.
        """
        ctx = InjectionContext(call_point="LLM#1")

        # System prompt — prefixed with Phoenix system goal (P042)
        ctx.system_prompt = (
            SYSTEM_GOAL + "\n\n"
            "You are a task classifier for the Phoenix Agent system. "
            "Your job is to classify the user's intent into one of the "
            "known task types and determine the appropriate output format."
        )

        # Task template with alias map
        template = self.templates.get_by_task_type(task_type)
        if template:
            ctx.task_template = template.description
            ctx.constraints.append(f"Task type: {template.task_type}")
            if template.required_capabilities:
                ctx.constraints.append(
                    f"Required capabilities: {', '.join(template.required_capabilities)}"
                )
        else:
            ctx.task_template = f"Classify task as: {task_type}"
            ctx.constraints.append(f"Task type: {task_type}")

        # Alias map injection
        if alias_map:
            ctx.kb_frameworks.append(
                "Alias table: " + json.dumps(alias_map, ensure_ascii=False)
            )

        # Output schema
        ctx.output_schema = {
            "type": "object",
            "required": ["task_type", "confidence", "sub_tasks"],
            "properties": {
                "task_type": {"type": "string"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "sub_tasks": {"type": "array", "items": {"type": "string"}},
            },
        }

        if extra_constraints:
            ctx.constraints.extend(extra_constraints)

        return ctx

    # ── LLM#2: Task decomposition ────────────────────────────

    def build_decompose_context(
        self,
        task_type: str,
        kb_protocols: Optional[list[str]] = None,
        last_round_protocols: Optional[list[str]] = None,
        max_subtask_count: int = 15,
        confirmation_statement: Optional[str] = None,
    ) -> InjectionContext:
        """Build context for LLM#2 — task decomposition (TEPv1) + KB framework mounting.

        TEPv1 enhancements:
            - Max subtask count enforced (default 15; >15 → advise user to decompose further)
            - Each subtask gets a locked method (intent-level statement for cross-session consistency)
            - Each subtask declares input_from / output_to (dependency chain)
            - Estimated duration in minutes (Agent time, approx 1/5~1/10 human time)

        Injects:
            - KB framework references
            - Duration estimation guidance (Issue 5)
            - Anti-bias directives (Issue 8)
            - TEPv1: granularity cap, method lock, dependency chain
        """
        ctx = InjectionContext(call_point="LLM#2")

        # System prompt — prefixed with Phoenix system goal (P042)
        ctx.system_prompt = (
            SYSTEM_GOAL + "\n\n"
            "你是一个任务分解引擎（Task Decomposition Engine, TEPv1）。\n"
            "将用户任务拆解为可独立执行的子任务序列。\n\n"

            "【子任务粒度约束（TEPv1）】\n"
            f"  - 子任务数量上限：{max_subtask_count}个。超过此上限 → 建议用户自行分解或分层处理\n"
            "  - 每个子任务应该是'一个LLM一轮交互可完成的原子操作'\n"
            "  - 子任务之间应保持松耦合，依赖关系通过 input_from / output_to 声明\n\n"

            "【方法锁定（TEPv1 — 防止跨会话执行漂移）】\n"
            "  - 每个子任务必须生成一个 method 字段：用一句话描述本步的核心执行方法\n"
            "  - method 是意图级声明（不是代码级实现细节），例如：\n"
            "    '汇总本周 Done 状态任务，按类型分组生成摘要表格'\n"
            "    '用 python-pptx 填充模板，将摘要表格渲染为 PPTX'\n"
            "  - method 锁定后在下一次执行时注入为 context，避免 LLM 随机改变执行方式\n\n"

            "【依赖声明（TEPv1 — 连载恢复依据）】\n"
            "  - input_from：上游依赖 [{\"from\": \"SUB-001\", \"asset\": \"tasks.json\"}]\n"
            "  - output_to：本步产出物路径或键名（例：\"sandbox/weekly_summary.md\"）\n"
            "  - 无依赖的子任务 input_from 为空数组 []\n\n"

            "【Toulmin 论证完整性要求（P061 — CP-123，仅用于 method 字段）】\n"
            "method 字段的决策理由须包含 Toulmin 6 要素结构：\n"
            "  - Claim（论断）→ Grounds（证据）→ Warrant（逻辑桥）→ Backing（桥支撑）\n"
            "  - Rebuttal（反例承认）→ Qualifier（限定词）\n"
            "若某要素不适用，标注'[不适用：<原因>]'，不得静默跳过。\n\n"

            "【耗时估算（Agent 时间，含 Planning Fallacy 缓冲）】\n"
            "  - 估算单位为分钟，参考 Agent 效率约为人的 5-10 倍\n"
            "  - 每个子任务标注 estimated_minutes\n"
            "  - 使用 P80 历史数据作为基线，乘以 1.3 作为规划缓冲\n"
        )

        # Inject confirmation_statement from LLM#3 if available
        if confirmation_statement:
            ctx.constraints.append(
                f"用户确认的任务理解：{confirmation_statement}"
            )

        # Task template
        template = self.templates.get_by_task_type(task_type)
        if template:
            ctx.task_template = (
                f"分解任务：{template.description}（框架：{template.framework_id}）"
            )
        else:
            ctx.task_template = f"分解任务类型：{task_type}"

        # KB frameworks
        if kb_protocols:
            ctx.kb_frameworks = kb_protocols
            ctx.constraints.append(
                f"使用以下KB框架作为主要参考：{', '.join(kb_protocols)}"
            )

        # Duration estimation (Issue 5: Planning Fallacy)
        estimated_seconds, duration_guidance = estimate_duration(
            task_type, self.decision_log_path
        )
        ctx.duration_guidance = duration_guidance
        ctx.constraints.append(
            f"总耗时估算基线：{estimated_seconds}s。{duration_guidance}"
        )

        # Anti-bias (Issue 8: Availability Heuristic)
        if kb_protocols and last_round_protocols:
            anti_bias = compute_anti_bias_directives(
                kb_protocols[:3], last_round_protocols
            )
            if anti_bias["biased"]:
                ctx.anti_bias_directives = anti_bias["directives"]
                ctx.constraints.append(
                    f"KB反偏已应用：协议 {anti_bias['overlapped_protocols']} "
                    f"权重降至 ×{0.7}"
                )

        # Output schema — TEPv1 decomposition
        ctx.output_schema = {
            "type": "object",
            "required": ["subtasks", "estimated_total_minutes", "risk_flags", "exceeds_granularity_limit"],
            "properties": {
                "subtasks": {
                    "type": "array",
                    "description": (
                        f"子任务序列，最多 {max_subtask_count} 项。"
                        f"每项是一个LLM一轮可完成的原子操作。"
                    ),
                    "items": {
                        "type": "object",
                        "required": [
                            "order", "subtask_id", "action", "estimated_minutes",
                            "method", "input_from", "output_to",
                        ],
                        "properties": {
                            "order": {"type": "integer"},
                            "subtask_id": {
                                "type": "string",
                                "description": "唯一标识，格式：SUB-{order:03d}",
                            },
                            "action": {
                                "type": "string",
                                "description": "一句话描述本步做什么",
                            },
                            "estimated_minutes": {
                                "type": "integer",
                                "description": "预估耗时（分钟），Agent 效率约为人的 5-10 倍",
                            },
                            "method": {
                                "type": "string",
                                "description": (
                                    "锁定方法声明（不可变）：包含 Toulmin 6 要素的意图级执行方法。"
                                    "跨会话连载时，此字段作为 context 注入以维持执行一致性。"
                                ),
                            },
                            "input_from": {
                                "type": "array",
                                "description": "上游依赖",
                                "items": {
                                    "type": "object",
                                    "required": ["from", "asset"],
                                    "properties": {
                                        "from": {"type": "string", "description": "依赖的子任务 ID"},
                                        "asset": {"type": "string", "description": "依赖的产出物"},
                                    },
                                },
                            },
                            "output_to": {
                                "type": "string",
                                "description": "本步产出物路径或键名，连载恢复和依赖检查用",
                            },
                            "tool_lock": {
                                "type": "string",
                                "description": "锁定工具关键词（可选），null 表示自由选择",
                            },
                        },
                    },
                },
                "estimated_total_minutes": {
                    "type": "integer",
                    "description": "所有子任务耗时总和（分钟），乘以 1.3 缓冲",
                },
                "risk_flags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "风险标记（如'依赖外部API'、'渲染可靠度不确定'）",
                },
                "exceeds_granularity_limit": {
                    "type": "boolean",
                    "description": (
                        f"若子任务数超过 {max_subtask_count}，设为 true，"
                        f"并在 subtasks 中按主题合并到 {max_subtask_count} 个以内。"
                    ),
                },
            },
        }

        return ctx

    # ── ER 完整性自检（远期指针 — CP-106）─────────────────────
    # 来源：CP-106 实体关系建模，改善任务拆解完整性。
    # 落地时在 build_decompose_context() 的 constraints 增加：
    #   - 任务涉及的所有「实体」是否已识别？（文件/目录/页面/用户/项目）
    #   - 实体间的关系是否已标注基数？（1:1 / 1:N / N:M）
    #   - 若遗漏实体 → 补充对应 step 或标注为「已知缺口」
    # 状态：远期 — 待 Guard v0.3 context_builder 重构时纳入

    # ── LLM#3: Information fill (TEPv1 three-tier) ────────────

    def build_fill_context(
        self,
        task_type: str,
        slot_map: Optional[dict[str, str]] = None,
        missing_fields: Optional[list[str]] = None,
        required_slots: Optional[list[dict]] = None,
    ) -> InjectionContext:
        """Build context for LLM#3 — information completion (TEPv1 three-tier).

        Three-tier slot classification:
            auto_fill     — derived from semantics/env, display for review.
            context_derive — inferred from history/prefs, present as guess + confirm.
            must_ask       — requires direct user input, ask clearly.

        Also generates a confirmation_statement: a natural language restatement
        of the full task understanding for the user to verify in one glance.

        Args:
            task_type: Task type string.
            slot_map: Known slots (pre-filled from context).
            missing_fields: Fields the caller already identifies as missing.
            required_slots: Task-type-specific required_slots definition
                            (from Task-Type-Registry.json).
        """
        ctx = InjectionContext(call_point="LLM#3")

        # System prompt — prefixed with Phoenix system goal (P042)
        ctx.system_prompt = (
            SYSTEM_GOAL + "\n\n"
            "你是一个信息补全引擎（Information Completion Engine, TEPv1）。\n"
            "任务信息分为三层：\n"
            "  1. auto_fill（自动填充）— 从语义/环境可推导的信息，展示给用户审阅即可\n"
            "  2. context_derive（上下文推导）— 从历史偏好/关联任务/协议推断，作为'猜测'呈现让用户确认\n"
            "  3. must_ask（必须询问）— 不可推导的关键信息，直接向用户提出清晰的问题\n\n"
            "重要原则：\n"
            "  - 能推导的不问，能猜测的只确认，不得不问的才问\n"
            "  - 生成一个 confirmation_statement：对用户原始意图的完整复述\n"
            "    （例：'您希望把本周已完成的任务清单汇总成周报，并以PDF格式输出，是这样吗？'）\n"
            "  - 即使全部字段自动填充，也要生成 confirmation_statement 让用户最终确认\n"
            "  - context_derive 项必须附上 basis（推断依据）\n"
            "  - must_ask 项必须附上 reason（为什么必须问，无法推导）"
        )

        # Task template
        template = self.templates.get_by_task_type(task_type)
        if template:
            ctx.task_template = (
                f"补全信息：{template.description}"
            )
        else:
            ctx.task_template = f"补全任务信息：{task_type}"

        # Inject required_slots from Task-Type-Registry if available
        if required_slots:
            ctx.constraints.append("任务类型的已知槽位定义：")
            for slot in required_slots:
                strat = slot.get("strategy", "must_ask")
                label = slot.get("label_cn", slot.get("name", "?"))
                default = slot.get("default_rule", "")
                example = slot.get("example_prompt", "")
                hint = f"  - {slot['name']}（{label}）— 推荐策略：{strat}"
                if default:
                    hint += f"；默认规则：{default}"
                if example and strat == "must_ask":
                    hint += f"；示例问法：{example}"
                ctx.constraints.append(hint)

        # Slot map — what's known, what's missing
        if slot_map:
            ctx.constraints.append("已知槽位：")
            for slot, value in slot_map.items():
                ctx.constraints.append(f"  - {slot}: {value}")

        if missing_fields:
            ctx.constraints.append("已知缺失字段：")
            for f in missing_fields:
                ctx.constraints.append(f"  - {f}")

        # Output schema — TEPv1 three-tier + confirmation_statement
        ctx.output_schema = {
            "type": "object",
            "required": ["auto_filled", "context_derived", "must_ask", "confirmation_statement"],
            "properties": {
                "confirmation_statement": {
                    "type": "string",
                    "description": (
                        "用自然语言完整复述你对用户意图的理解，让用户一眼确认。"
                        "格式：'您希望[动作]，以[格式]输出，[补充约束]，是这样吗？'"
                        "例：'您希望把本周已完成的任务清单汇总成周报，并以PDF格式输出，是这样吗？'"
                    ),
                },
                "auto_filled": {
                    "type": "object",
                    "description": (
                        "自动填充的槽位。从语义、环境、仓库结构推导。"
                        "展示给用户审阅即可，无需额外提问。"
                    ),
                    "additionalProperties": {"type": "string"},
                },
                "context_derived": {
                    "type": "array",
                    "description": (
                        "从历史偏好/关联任务/协议推断的槽位。作为'猜测'呈现，让用户确认。"
                    ),
                    "items": {
                        "type": "object",
                        "required": ["field", "guessed_value", "basis"],
                        "properties": {
                            "field": {"type": "string"},
                            "guessed_value": {"type": "string"},
                            "basis": {
                                "type": "string",
                                "description": "推断依据：基于什么历史/偏好/协议？",
                            },
                        },
                    },
                },
                "must_ask": {
                    "type": "array",
                    "description": (
                        "不可推导的关键信息，必须直接向用户提问。"
                        "仅包含真正阻塞执行的信息，不过度提问。"
                    ),
                    "items": {
                        "type": "object",
                        "required": ["field", "question", "reason"],
                        "properties": {
                            "field": {"type": "string"},
                            "question": {"type": "string"},
                            "reason": {
                                "type": "string",
                                "description": "为何必须提问（无法推导的原因）",
                            },
                        },
                    },
                },
            },
        }

        ctx.constraints.append(
            "禁止猜测 marked_as_user_input_required 类型的字段值。"
            "能推导的放 auto_filled，能推测的放 context_derived 并附 basis，"
            "真正阻塞的才放 must_ask。过度提问会降低用户体验。"
        )

        return ctx
