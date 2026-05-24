"""Dimension enums, R/C track mapping tables, and KB downgrade logic."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import ClassVar


# ── Dimension Enums ──────────────────────────────────────────────


class SLevel(IntEnum):
    """Impact Scope — S0~S3"""
    SINGLE_FILE  = 0  # single file / single point
    SINGLE_MODULE = 1  # single module / service
    CROSS_MODULE  = 2  # cross-module / cross-service
    CROSS_SYSTEM  = 3  # cross-system / global


class RevLevel(IntEnum):
    """Reversibility — Rev0~Rev3"""
    FULLY_REVERSIBLE = 0  # local snapshot rollback
    PARTIALLY        = 1  # needs manual intervention
    HARD_TO_ROLLBACK = 2  # cross-module state coupling
    IRREVERSIBLE     = 3  # delete / migration / no rollback


class ALevel(IntEnum):
    """Ambiguity — A0~A3"""
    CLEAR_TARGET     = 0  # clear goal & boundary
    DIRECTION_CLEAR  = 1  # direction clear, details fuzzy
    KEY_TARGET_UNCLEAR = 2  # key goals unclear, needs clarification
    UNDEFINED_TASK   = 3  # task not defined, needs reverse questioning


class CLevel(IntEnum):
    """Creativity — C0~C3 (independent track)"""
    NONE       = 0  # pure logic / execution
    LOW        = 1  # tweak within existing framework
    MEDIUM     = 2  # create within user-given boundary
    HIGH       = 3  # original creation, new structure


class ELevel(IntEnum):
    """外部操作风险 External Reversibility — E0~E3"""
    NO_EXTERNAL_DEP     = 0  # pure local
    READ_ONLY_EXTERNAL  = 1  # WebSearch, Fetch, read Notion
    REVERSIBLE_WRITE    = 2  # write Notion page (version history)
    IRREVERSIBLE_WRITE  = 3  # payment, force delete, mass email


class AuthLevel(IntEnum):
    """外部暴露 External Exposure — Auth0~Auth3"""
    ZERO       = 0  # pure local
    READ_ONLY  = 1  # WebSearch, Fetch, read MCP
    CONTROLLED = 2  # create/edit designated Notion page
    IRREVERSIBLE = 3  # delete disk, force push main, prod config


class VLevel(IntEnum):
    """Value Conflict — V0~V3 (DEPRECATED: not in L-level calculation since 2026-05-22).
    
    Kept for future decision assist system. V measures plan-selection opportunity
    cost — an internal cost function, not a risk dimension. Does NOT affect L level.
    """
    NONE      = 0  # single objective
    MILD      = 1  # Agent can suggest
    MODERATE  = 2  # needs user preference
    HIGH      = 3  # efficiency vs completeness trade-off


class KLevel(IntEnum):
    """Knowledge Coverage — K0~K3 (C track, doesn't push L up)"""
    FULL_COVER     = 0  # domain has matching protocols, ≥1 validated
    PARTIAL_COVER  = 1  # domain has matching protocols, all unvalidated
    GAP_COVER      = 2  # domain known, no specific protocol
    ZERO_COVER     = 3  # brand new domain, zero protocols


# ── C-Track sub-dimension ────────────────────────────────────────


class CInfoMode(IntEnum):
    """Information processing mode (auxiliary, does NOT affect L)."""
    PATTERN    = 0  # has mental representation, fast pattern matching
    ANALYTICAL = 1  # no mental representation, per-item reasoning


# ── R-Track dimension→L mapping ──────────────────────────────────

R_TRACK_MAP: ClassVar[dict[str, dict[int, int]]] = {
    "S":    {0: 0, 1: 0, 2: 2, 3: 3},
    "Rev":  {0: 0, 1: 1, 2: 2, 3: 3},
    "A":    {0: 0, 1: 1, 2: 2, 3: 2},
    "E":    {0: 0, 1: 0, 2: 1, 3: 3},
    "Auth": {0: 0, 1: 0, 2: 1, 3: 3},
    # V removed from R track (2026-05-22) — opportunity cost is an internal cost
    # function, not a risk dimension. V computation kept for future decision
    # assist system but does NOT affect L level.
}

# ── K-Track dimension→L mapping ──────────────────────────────────
# Formerly "C_TRACK_MAP". C dimension removed from L calculation
# (2026-05-23): C is now an agent-behavior metadata field, not a risk factor.
# See compute_C_deviation_L() for the delta model.

K_TRACK_MAP: ClassVar[dict[str, dict[int, int]]] = {
    "K": {0: 0, 1: 0, 2: 2, 3: 2},  # K2+: knowledge gap needs user direction
}

# Backward-compat alias (for transition)
C_TRACK_MAP = K_TRACK_MAP

# ── Forced L3 conditions ─────────────────────────────────────────

FORCED_L3_DIMS: ClassVar[set[str]] = {"S", "Rev", "Auth", "E"}
FORCED_L3_VALUE: ClassVar[int] = 3

# ── User-facing dimension labels (Chinese) ────────────────────────

DIM_LABELS_CN: dict[str, dict[int, str]] = {
    "S": {
        0: "单文件/单点影响",
        1: "单模块/单服务影响",
        2: "跨模块/跨服务影响",
        3: "跨系统/全局影响",
    },
    "Rev": {
        0: "完全可逆",
        1: "部分可逆，需人工介入",
        2: "难以回滚",
        3: "不可逆",
    },
    "A": {
        0: "目标明确，边界清晰",
        1: "方向清晰，细节待定",
        2: "关键目标不明确",
        3: "任务未定义，需澄清",
    },
    "C": {
        0: "纯逻辑/纯执行",
        1: "在既有框架内微调",
        2: "需要构思，边界由你给定",
        3: "原创/发散/构建新结构",
    },
    "E": {
        0: "纯本地，无外部系统",
        1: "只读外部（搜索/查询）",
        2: "可撤回的外部写入",
        3: "不可撤回的外部写入",
    },
    "Auth": {
        0: "零暴露",
        1: "只读外部",
        2: "可控写入",
        3: "不可逆/广域写入",
    },
    "K": {
        0: "全覆盖，有已验证的操作协议",
        1: "部分覆盖，协议全部未验证",
        2: "缺口覆盖，域已知但无特定协议",
        3: "零覆盖，全新领域，无协议",
    },
}

DIM_NAMES_CN: dict[str, str] = {
    "S": "影响范围",
    "Rev": "可逆性",
    "A": "模糊度",
    "C": "创意度",
    "E": "外部操作风险",
    "Auth": "外部暴露",
    "K": "知识覆盖度",
}

# ── KB downgrade rules ───────────────────────────────────────────


@dataclass(frozen=True)
class KBContext:
    """Context from Step 2-KB knowledge brain preload."""
    protocols_activated: list[str]   # matched protocol IDs (CP-xxx)
    validated_count: int             # number of validated protocols among activated


def apply_kb_downgrade(
    a_level: int, c_level: int, kb: KBContext | None
) -> tuple[int, int]:
    """Apply KB preload downgrade to A and C dimensions.

    Downgrade rule (from mod-decision-framework.mdc):
        If kb_protocols_activated has ≥1 validated_count ≥ 1:
            A drops 1 level (floor 0)
            C drops 1 level (floor 0)
    """
    if kb is None or not kb.protocols_activated or kb.validated_count < 1:
        return a_level, c_level

    a_new = max(0, a_level - 1)
    c_new = max(0, c_level - 1)
    return a_new, c_new




def compute_C_deviation_L(C_agent: int, C_expected: int) -> tuple[int | None, str]:
    """Compute execution-level (L) from creativity (C) deviation.

    2026-05-23: C维度重构为「方案发散度约束」——C 不再参与风险-L 映射。
    改为差额模型：C_agent - C_expected → 执行对齐等级。

    Args:
        C_agent: Agent 当前方案的实际创意度 (0-3)
        C_expected: 任务类型预期的创意度天花板 (0-3)

    Returns:
        (L_from_C or None, deviation_description)
        None = C 无偏差，不干预 L 级
    """
    delta = C_agent - C_expected
    if delta <= 0:
        return None, ""
    L_from_C = min(delta, 3)
    if L_from_C == 1:
        desc = "告知执行"
    elif L_from_C == 2:
        desc = "确认执行"
    else:
        desc = "高风险分析"
    return L_from_C, desc

# ── Opportunity Cost (P128, 2026-05-21) ───────────────────────────

# Default opportunity cost threshold — above this, the current plan's
# opportunity cost is considered "significant" and should trigger
# a re-evaluation or AskQuestion.
OPPORTUNITY_COST_THRESHOLD: float = 0.15


def compute_opportunity_cost(
    plan_a_benefit: float,
    plan_b_benefit: float,
    plan_a_confidence: float = 1.0,
    plan_b_confidence: float = 1.0,
) -> float:
    """Compute the opportunity cost of choosing plan A over plan B.

    CP-128 机会成本与边际决策思维:
        机会成本 = 次优方案的期望收益 - 当前方案的期望收益

    如果 result > 0: 当前方案的机会成本为正 → 应转向或至少告知用户。
    如果 result ≤ 0: 当前方案是最优选择。

    Args:
        plan_a_benefit: Normalized expected benefit of plan A (0.0-1.0).
        plan_b_benefit: Normalized expected benefit of the best alternative.
        plan_a_confidence: Confidence in plan A's benefit estimate.
        plan_b_confidence: Confidence in plan B's benefit estimate.

    Returns:
        opportunity_cost: plan B 期望收益 - plan A 期望收益。
    """
    a_expected = min(max(plan_a_benefit, 0.0), 1.0) * min(max(plan_a_confidence, 0.0), 1.0)
    b_expected = min(max(plan_b_benefit, 0.0), 1.0) * min(max(plan_b_confidence, 0.0), 1.0)
    return round(b_expected - a_expected, 4)


# ── V-Dimension Opportunity Cost Integration (P066, 2026-05-22) ──

def compute_V_from_opportunity_cost(
    opportunity_cost: float,
    plan_a_label: str = "方案A",
    plan_b_label: str = "方案B",
) -> tuple[int, str]:
    """Compute V-dimension level from quantified opportunity cost.

    CP-128 机会成本与边际决策思维: Replaces the fuzzy V-dimension judgment
    ('value conflict') with quantified opportunity cost.

    V-level mapping:
        V0: cost ≤ 0 (current plan is optimal, no value conflict)
        V1: 0 < cost ≤ THRESHOLD (Agent can suggest alternative)
        V2: THRESHOLD < cost ≤ 2*THRESHOLD (needs user preference)
        V3: cost > 2*THRESHOLD (efficiency vs completeness trade-off — high conflict)

    Args:
        opportunity_cost: plan_b期望 - plan_a期望 (from compute_opportunity_cost())
        plan_a_label: Human-readable label for plan A.
        plan_b_label: Human-readable label for plan B.

    Returns:
        (v_level: 0-3, disclaimer: 放弃声明字符串)
    """
    if opportunity_cost <= 0:
        disclaimer = (
            f"机会成本 = {opportunity_cost:.2f}——"
            f"当前方案（{plan_a_label}）是最优选择，"
            f"次优方案（{plan_b_label}）的期望收益不高于它。"
        )
        return 0, disclaimer

    t = OPPORTUNITY_COST_THRESHOLD
    if opportunity_cost <= t:
        disclaimer = (
            f"机会成本 = {opportunity_cost:.2f}（< 阈值 {t}）——"
            f"选择{plan_a_label}意味着放弃{plan_b_label}的 {opportunity_cost:.0%} 收益。"
            f"边际损失在可接受范围内，Agent 可自行建议替代方案。"
        )
        return 1, disclaimer
    elif opportunity_cost <= 2 * t:
        disclaimer = (
            f"机会成本 = {opportunity_cost:.2f}（超过阈值 {t}）——"
            f"选择{plan_a_label}意味着放弃{plan_b_label}的 {opportunity_cost:.0%} 收益。"
            f"建议询问用户偏好再决定。"
        )
        return 2, disclaimer
    else:
        disclaimer = (
            f"机会成本 = {opportunity_cost:.2f}（远超阈值 2×{t}）——"
            f"选择{plan_a_label}意味着放弃{plan_b_label}的 {opportunity_cost:.0%} 收益。"
            f"效率与完整性的重大冲突，强烈建议用户重新评估。"
        )
        return 3, disclaimer


# ── Toulmin Argument Completeness Check (P061, 2026-05-21) ────────

def check_toulmin_completeness(decision_rationale: str) -> dict:
    """Lightweight Toulmin 6-element completeness check for agent decision rationales.

    CP-123 Toulmin六要素模型: 一个完整的论证应包含 Claim/Grounds/Warrant/
    Backing/Rebuttal/Qualifier。本函数基于关键词+结构模式做轻量检测，不调用LLM。

    Args:
        decision_rationale: The agent's decision rationale text.

    Returns:
        {
            "complete": bool,              # ≥4 of 6 elements detected
            "elements_found": [...],        # which 6 elements were detected
            "missing": [...],               # which elements are missing
            "score": float,                 # 0.0-1.0 completeness ratio
            "evidence_count": int,          # sub-indicator: number of evidence/data points mentioned
            "warrant_explicitness": int,    # sub-indicator: 0=implicit, 1=weak, 2=explicit bridge
            "rebuttal_awareness": int,      # sub-indicator: 0=none, 1=mentioned, 2=substantive counter
        }
    """
    # Detection heuristics — keyword + pattern per element
    patterns = {
        "Claim": {
            "keywords": ["结论", "判定", "决策", "建议", "应", "应该", "因此", "所以",
                         "conclusion", "therefore", "recommend", "decided"],
            "check": lambda t: any(kw in t for kw in ["结论", "判定", "建议", "therefore", "recommend"]),
        },
        "Grounds": {
            "keywords": ["证据", "数据显示", "日志", "结果", "测试", "错误", "输出",
                         "evidence", "log", "test result", "output shows", "because"],
            "check": lambda t: any(kw in t for kw in ["证据", "数据", "日志", "结果", "because", "log", "test"]),
        },
        "Warrant": {
            "keywords": ["因为", "基于", "依据", "原理", "规则", "标准",
                         "since", "based on", "according to", "principle"],
            "check": lambda t: any(kw in t for kw in ["因为", "基于", "依据", "原理", "since", "based on"]),
        },
        "Backing": {
            "keywords": ["验证", "原论文", "官方文档", "来源", "经过测试",
                         "proven", "documented", "verified", "source"],
            "check": lambda t: any(kw in t for kw in ["验证", "论文", "官方", "来源", "documented", "verified"]),
        },
        "Rebuttal": {
            "keywords": ["但", "除非", "例外", "如果", "但是", "反之", "反例",
                         "however", "unless", "except", "but if", "on the other hand"],
            "check": lambda t: any(kw in t for kw in ["但", "除非", "例外", "反", "however", "unless", "except"]),
        },
        "Qualifier": {
            "keywords": ["大概", "可能", "应该只", "概率", "置信度", "不确定",
                         "probably", "likely", "confidence", "may", "might", "possibly"],
            "check": lambda t: any(kw in t for kw in ["大概", "可能", "概率", "置信度", "probably", "likely", "confidence"]),
        },
    }

    text_lower = decision_rationale.lower()
    elements_found = []
    missing = []

    for element, config in patterns.items():
        if config["check"](text_lower):
            elements_found.append(element)
        else:
            missing.append(element)

    score = len(elements_found) / 6.0
    complete = score >= 0.5  # ≥3 out of 6

    # ── P061: Three sub-indicators ─────────────────────────────
    # evidence_count: count of distinct evidence/data/log references
    evidence_keywords = ["证据", "数据", "日志", "错误码", "输出", "结果", "测试",
                         "evidence", "log", "error", "output", "test result", "stack trace"]
    evidence_count = sum(1 for kw in evidence_keywords if kw in text_lower)
    evidence_count = min(evidence_count, 5)  # cap at 5

    # warrant_explicitness: how explicit is the logical bridge?
    #   2 = explicit bridge (contains both "因为/基于" AND "所以/因此/因而")
    #   1 = weak bridge (has one side of the bridge)
    #   0 = implicit (no bridge structure detected)
    has_reason = any(kw in text_lower for kw in ["因为", "基于", "依据", "since", "based on", "because"])
    has_conclusion = any(kw in text_lower for kw in ["因此", "所以", "因而", "therefore", "thus", "hence"])
    if has_reason and has_conclusion:
        warrant_explicitness = 2
    elif has_reason or has_conclusion:
        warrant_explicitness = 1
    else:
        warrant_explicitness = 0

    # rebuttal_awareness: how substantive is the counter-argument?
    #   2 = substantive counter (names a specific condition/exception with reasoning)
    #   1 = mentioned (uses "但"/"除非"/"例外" but superficially)
    #   0 = none (no counter-argument at all)
    rebuttal_simple = any(kw in text_lower for kw in ["但", "但是", "除非", "例外", "however", "except"])
    rebuttal_substantive = any(kw in text_lower for kw in ["反例", "反之", "如果是", "当...时", "rebuttal",
                                                            "counter", "on the other hand", "that said"])
    if rebuttal_substantive:
        rebuttal_awareness = 2
    elif rebuttal_simple:
        rebuttal_awareness = 1
    else:
        rebuttal_awareness = 0

    return {
        "complete": complete,
        "elements_found": elements_found,
        "missing": missing,
        "score": round(score, 2),
        "evidence_count": evidence_count,
        "warrant_explicitness": warrant_explicitness,
        "rebuttal_awareness": rebuttal_awareness,
    }


def toulmin_injection_prompt(missing_elements: list[str]) -> str:
    """Generate a prompt injection for LLM#2 to request missing Toulmin elements.

    Args:
        missing_elements: List of element names not found in the rationale.

    Returns:
        A string to inject into the LLM#2 system_prompt.
    """
    if not missing_elements:
        return ""

    mapping = {
        "Grounds": "请提供具体的证据或数据支撑你的决策理由（Grounds/Data）。",
        "Warrant": "请说明证据如何支持结论的逻辑桥（Warrant）——为什么这些证据能得出这个结论？",
        "Rebuttal": "请思考并指出：这个决策在什么情况下是错误的？识别至少 1 个反例或例外（Rebuttal）。",
        "Backing": "请为逻辑桥提供支撑依据（Backing）——例如引用来源、协议编号、历史经验。",
        "Qualifier": "请标注结论的确定性（Qualifier）——这是大概率/确定/有待验证？",
        "Claim": "请明确陈述该决策的核心论断（Claim）。",
    }

    parts = ["\n【Toulmin 论证完整性要求（CP-123）】"]
    for elem in missing_elements:
        if elem in mapping:
            parts.append(f"- {mapping[elem]}")
    parts.append(f"当前缺失: {', '.join(missing_elements)}")
    return "\n".join(parts)


# ── Lollapalooza 因子叠加扫描 (P063, 2026-05-21) ────────────────

def scan_lollapalooza_risk(
    activated_factor_ids: list[str],
    registry_path: str = "",
) -> dict:
    """Scan triggered factors for Lollapalooza effect (P063).

    CP-119 Lollapalooza效应: ≥3 种同向叠加的低风险因子 → 非线性放大。
    从 CP-125 的 14 类逻辑谬误中提取因子定义，存储于 factor_registry.json。

    Args:
        activated_factor_ids: List of factor IDs (CF-xxx) active in this round.
        registry_path: Path to factor_registry.json (default: sibling to dimensions.py).

    Returns:
        {
            "lollapalooza": bool,                # ≥3 因子同向触发
            "factor_count": int,                  # 触发的因子数
            "direction_dominance": dict,           # {direction_key: count}
            "dominant_direction": str,             # 主导方向 (认知偏差/执行偏差/决策偏差)
            "homogeneity": float,                  # 同向性比例 (0-1)
            "escalation": str,                     # "none" / "yellow" / "red"
            "message": str,                        # 可注入到 Agent 上下文的预警信息
        }
    """
    import json
    from pathlib import Path

    if not activated_factor_ids or len(activated_factor_ids) < 3:
        return {
            "lollapalooza": False,
            "factor_count": len(activated_factor_ids or []),
            "direction_dominance": {},
            "dominant_direction": "",
            "homogeneity": 0.0,
            "escalation": "none",
            "message": "",
        }

    if not registry_path:
        registry_path = str(Path(__file__).parent / "factor_registry.json")

    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "lollapalooza": False,
            "factor_count": len(activated_factor_ids),
            "direction_dominance": {},
            "dominant_direction": "",
            "homogeneity": 0.0,
            "escalation": "none",
            "message": f"因子注册表 {registry_path} 不可用，跳过 Lollapalooza 扫描",
        }

    factors = {f["factor_id"]: f for f in registry.get("factors", [])}
    rules = registry.get("lollapalooza_rules", {})
    threshold = rules.get("trigger_threshold", 3)
    dir_groups = rules.get("direction_groups", {})

    # Collect direction + weight for activated factors
    activated: list[dict] = []
    for fid in activated_factor_ids:
        if fid in factors:
            activated.append(factors[fid])

    if len(activated) < threshold:
        return {
            "lollapalooza": False,
            "factor_count": len(activated),
            "direction_dominance": {},
            "dominant_direction": "",
            "homogeneity": 0.0,
            "escalation": "none",
            "message": f"仅 {len(activated)} 个因子触发，未达 Lollapalooza 阈值 {threshold}",
        }

    # Count by direction GROUP (not raw direction string)
    # Map each factor to its group from direction_groups registry
    factor_direction_map: dict[str, str] = {}
    for group_name, group_info in dir_groups.items():
        for gid in group_info.get("factors", []):
            factor_direction_map[gid] = group_name

    direction_count: dict[str, int] = {}
    for f in activated:
        fid = f["factor_id"]
        g = factor_direction_map.get(fid, f.get("direction", "未知"))
        direction_count[g] = direction_count.get(g, 0) + 1

    # Dominant direction + homogeneity
    dominated = max(direction_count.values())
    homogeneity = dominated / len(activated)
    dominant = max(direction_count, key=direction_count.get)  # type: ignore[arg-type]

    lollapalooza = homogeneity >= 0.6

    # Escalation
    escalation_type = rules.get("escalation", {})
    escalation = "none"
    if lollapalooza:
        if len(activated) >= 5 or (len(activated) >= threshold and homogeneity > 0.8):
            escalation = "red"
        else:
            escalation = "yellow"

    # Build message
    factor_names = [f["name"] for f in activated]
    if lollapalooza:
        if escalation == "red":
            msg = (
                f"🚨 Lollapalooza 红色预警：{len(activated)} 个因子触发，"
                f"主导方向'{dominant}'（同向性 {homogeneity:.0%}）。"
                f"触发因子：{', '.join(factor_names)}。"
                f"多重偏差同向叠加，风险非线性放大——强制 L3 审视。"
            )
        else:
            msg = (
                f"⚠ Lollapalooza 黄色预警：{len(activated)} 个因子触发，"
                f"主导方向'{dominant}'（同向性 {homogeneity:.0%}）。"
                f"触发因子：{', '.join(factor_names)}。"
                f"建议暂停自检。"
            )
    else:
        msg = (
            f"📊 {len(activated)} 个因子触发但方向分散，"
            f"主导方向'{dominant}'（同向性 {homogeneity:.0%}），未达 Lollapalooza 阈值。"
        )

    return {
        "lollapalooza": lollapalooza,
        "factor_count": len(activated),
        "direction_dominance": {d: c for d, c in sorted(direction_count.items(), key=lambda x: -x[1])},
        "dominant_direction": dominant,
        "homogeneity": round(homogeneity, 2),
        "escalation": escalation,
        "message": msg,
    }
