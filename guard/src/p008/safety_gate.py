"""Safety Gate — high-risk operation interceptor for Guard MVP v0.1.

Detects dangerous shell commands via regex patterns and enforces a
mandatory red-alert flow: pause → echo → cwd check → preview → AskQuestion.

Architecture:
    safety_gate.py is a standalone module — zero dependency on P008.
    It can be called independently via its public API, or through Guard's
    main pipeline.

Patterns are derived from flow-high-risk-safety.mdc §触发条件:
    1. Recursive delete  (rm -rf / del /s / Remove-Item -Recurse / rmdir /s / rd /s)
    2. Wildcard kill      (taskkill /f /im / killall / pkill / Stop-Process -Name *)
    3. Cross-drive ops     (path starts with different drive letter + recursive delete)
    4. Git destructive     (reset --hard / clean -fdx / checkout -- <wildcard>)
    5. Out-of-workspace    (target path not under repo root)
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar


# ── Regex patterns ─────────────────────────────────────────────────

# 1. Recursive delete patterns
RECURSIVE_DELETE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*)\b", re.IGNORECASE),  # rm -rf / -r / -fr
    re.compile(r"\brmdir\s+/[sq]\b", re.IGNORECASE),                 # rmdir /s /q
    re.compile(r"\brd\s+/[sq]\b", re.IGNORECASE),                    # rd /s /q
    re.compile(r"\bdel\s+/[sq]\b", re.IGNORECASE),                   # del /s
    re.compile(r"Remove-Item\s+-Recurse", re.IGNORECASE),             # PowerShell
]

# 2. Wildcard process kill patterns
WILDCARD_KILL_PATTERNS: list[re.Pattern] = [
    re.compile(r"\btaskkill\s+/f\s+/im\s+\S+", re.IGNORECASE),       # Windows
    re.compile(r"\bkillall\b", re.IGNORECASE),                        # Linux
    re.compile(r"\bpkill\b", re.IGNORECASE),                          # Linux
    re.compile(r"Stop-Process\s+-Name\s+\*", re.IGNORECASE),          # PowerShell
]

# 3. Cross-drive operations (recursive delete with drive letter)
CROSS_DRIVE_PATTERNS: list[re.Pattern] = [
    # rm -rf with a Windows drive path (e.g. rm -rf D:\foo)
    re.compile(
        r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*)\s+[A-Za-z]:\\",
        re.IGNORECASE,
    ),
    re.compile(
        r"Remove-Item\s+-Recurse\s+[A-Za-z]:\\",
        re.IGNORECASE,
    ),
    re.compile(
        r"\brmdir\s+/[sq]\s+[A-Za-z]:\\",
        re.IGNORECASE,
    ),
    re.compile(
        r"\brd\s+/[sq]\s+[A-Za-z]:\\",
        re.IGNORECASE,
    ),
    # Path ending with root slash (D:\) — not a real path, likely typo
    re.compile(r"[A-Za-z]:\\(?:Users|Windows|Program)\\", re.IGNORECASE),  # system dirs
]

# 4. Git destructive patterns
GIT_DESTRUCTIVE_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE),
    re.compile(r"\bgit\s+clean\s+-[a-z]*f[a-z]*d[a-z]*x[a-z]*\b", re.IGNORECASE),  # -fdx, -xdf, -fd
    # git checkout -- <wildcard or non-specific path>
    re.compile(r"\bgit\s+checkout\s+--\s+(\*|\.|%|%[A-Z])", re.IGNORECASE),
    # git push --force (destructive to remote)
    re.compile(r"\bgit\s+push\s+.*--force\b", re.IGNORECASE),
    re.compile(r"\bgit\s+push\s+.*-f\b", re.IGNORECASE),
]

# 5. Out-of-workspace path patterns (system directories)
OUT_OF_WORKSPACE_PATTERNS: list[re.Pattern] = [
    re.compile(r"[A-Za-z]:\\(?:Windows|Program\s+Files|Users)\\"),
    re.compile(r"/etc/"),
    re.compile(r"/usr/"),
    re.compile(r"/var/"),
    re.compile(r"/tmp/"),
    re.compile(r"C:\\\\", re.IGNORECASE),        # root of C drive
    re.compile(r"D:\\\\", re.IGNORECASE),        # root of D drive
    re.compile(r"\brm\s+.*\s+/[a-z]", re.IGNORECASE),        # rm targeting ABSOLUTE path (starts with /)
]


@dataclass
class SafetyGateResult:
    """Result of a safety gate check."""

    is_high_risk: bool
    risk_type: str = ""                     # "recursive_delete" | "wildcard_kill" | "cross_drive" | "git_destructive" | "out_of_workspace"
    command: str = ""                       # original command string
    matched_patterns: list[str] = field(default_factory=list)  # which regex(es) matched
    recommended_gate: str = ""              # "red_alert" | "ask_confirm" | "pass"
    exceptions_apply: list[str] = field(default_factory=list)  # any exception rules that matched

    # Red-alert flow outputs (filled by steps 1-4)
    cwd: str = ""
    impact_preview: str = ""
    preview_command: str = ""


# ── Core detection logic ──────────────────────────────────────────


class SafetyGate:
    """High-risk command detector and red-alert flow enforcer.

    Usage:
        gate = SafetyGate(workspace_root="D:/Phoenix/cursor-knowledge")
        result = gate.check("rm -rf D:\\test\\")
        if result.is_high_risk:
            gate.run_red_alert(result)
    """

    # ── Exception rules ──────────────────────────────────────

    # Git staging-area operations that are safe
    _GIT_SAFE_PATTERNS: ClassVar[list[re.Pattern]] = [
        re.compile(r"\bgit\s+reset\s+HEAD\s+\S+"),     # git reset HEAD <file>
        re.compile(r"\bgit\s+restore\s+--staged\s+"),   # git restore --staged
    ]

    # .trash directory — safe for non-recursive deletes
    _TRASH_SAFE_PATTERN: ClassVar[re.Pattern] = re.compile(r"\b\.trash[/\\]", re.IGNORECASE)

    def __init__(self, workspace_root: str | Path = "") -> None:
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
        # Convert to absolute for comparison
        self.workspace_root = self.workspace_root.resolve()

    # ── Public API ───────────────────────────────────────────

    def check(self, command: str, user_authorized: bool = False) -> SafetyGateResult:
        """Check a shell command for high-risk patterns.

        Args:
            command: The exact shell command to check.
            user_authorized: True if user has given global authorization this session.

        Returns:
            SafetyGateResult with is_high_risk and risk_type.
        """
        if user_authorized:
            return SafetyGateResult(
                is_high_risk=False,
                command=command,
                recommended_gate="pass",
                exceptions_apply=["user_authorized"],
            )

        # Check each trigger category
        result = SafetyGateResult(command=command, is_high_risk=False)

        # 1. Recursive delete
        for pat in RECURSIVE_DELETE_PATTERNS:
            if pat.search(command):
                # Check exceptions
                if self._is_trash_safe(command) and not self._is_recursive_with_path(command):
                    result.exceptions_apply.append("trash_non_recursive")
                    continue
                result.is_high_risk = True
                result.risk_type = "recursive_delete"
                result.matched_patterns.append(pat.pattern)

        # 2. Wildcard kill
        for pat in WILDCARD_KILL_PATTERNS:
            if pat.search(command):
                result.is_high_risk = True
                result.risk_type = "wildcard_kill"
                result.matched_patterns.append(pat.pattern)

        # 3. Cross-drive
        for pat in CROSS_DRIVE_PATTERNS:
            if pat.search(command):
                result.is_high_risk = True
                result.risk_type = "cross_drive"
                result.matched_patterns.append(pat.pattern)

        # 4. Git destructive
        for pat in GIT_DESTRUCTIVE_PATTERNS:
            if pat.search(command):
                # Check git-safe exceptions
                if self._is_git_safe(command):
                    result.exceptions_apply.append("git_staging_only")
                    continue
                result.is_high_risk = True
                result.risk_type = "git_destructive"
                result.matched_patterns.append(pat.pattern)

        # 5. Out of workspace
        for pat in OUT_OF_WORKSPACE_PATTERNS:
            if pat.search(command):
                result.is_high_risk = True
                result.risk_type = "out_of_workspace"
                result.matched_patterns.append(pat.pattern)

        if result.is_high_risk:
            result.recommended_gate = "red_alert"
        else:
            result.recommended_gate = "pass"

        return result

    def run_red_alert(self, result: SafetyGateResult) -> SafetyGateResult:
        """Execute the red-alert flow steps 1-4 (information gathering only).

        Steps:
            1. Pause — already done (we're in the check).
            2. Echo command — stored in result.command.
            3. Show CWD — stored in result.cwd.
            4. Preview impact — build preview command, stored in result.

        Returns the result with cwd and preview filled in.
        """
        # Step 3: Show CWD
        result.cwd = str(Path.cwd())

        # Step 4: Build preview command based on risk type
        if result.risk_type == "recursive_delete":
            # Try to extract the target path from the command
            target = self._extract_target_path(result.command)
            if self._is_windows():
                result.preview_command = f"dir \"{target}\" 2>nul"
            else:
                result.preview_command = f"ls -la \"{target}\" 2>/dev/null"
            result.impact_preview = f"Preview files to be deleted at: {target}"

        elif result.risk_type == "wildcard_kill":
            proc_name = self._extract_process_name(result.command)
            if self._is_windows():
                result.preview_command = f"tasklist /fi \"imagename eq {proc_name}\""
            else:
                result.preview_command = f"ps aux | grep {proc_name}"
            result.impact_preview = f"Preview processes matching: {proc_name}"

        elif result.risk_type == "git_destructive":
            result.preview_command = "git status --short"
            result.impact_preview = "Git working tree status before destructive operation"

        elif result.risk_type == "cross_drive":
            target = self._extract_target_path(result.command)
            if self._is_windows():
                result.preview_command = f"dir \"{target}\" 2>nul"
            result.impact_preview = f"Cross-drive operation detected at: {target}"

        elif result.risk_type == "out_of_workspace":
            result.preview_command = "echo 'Target is outside workspace — cannot safely preview'"
            result.impact_preview = "Target path is outside the repository workspace"

        return result

    def format_ask_question_prompt(self, result: SafetyGateResult) -> dict:
        """Build the AskQuestion format for step 5.

        Returns a dict suitable for AskQuestion tool formatting.
        P029 requirement: dual-frame — benefits first, then risks.
        P062 (2026-05-21): ARS 轻量论证评估 — 对每个拦截项标注
            A (Acceptability 前提可接受?) / R (Relevance 相关?) / S (Sufficiency 充分?)。
            ARS 全不通过 → 追加'强制确认'标记。
        """
        ars = self._assess_ars(result)

        prompt = {
            "title": "[WARNING] High-Risk Operation",
            "command_full": result.command,
            "risk_type": result.risk_type,
            "cwd": result.cwd,
            "impact_preview": result.impact_preview,
            "preview_command": result.preview_command,
            "matched_triggers": result.matched_patterns,
            "options": [
                {
                    "id": "confirm",
                    "label": f"[确认执行] {result.command[:80]}{'…' if len(result.command) > 80 else ''}",
                },
                {"id": "cancel", "label": "[取消]"},
            ],
        }

        # ── P062: ARS 轻量论证评估 ────────────────────────────
        if result.is_high_risk:
            prompt["ars_assessment"] = ars
            if ars["all_failed"]:
                prompt["title"] += " / ARS 三重不通过 — 见论证评估"
                prompt["ars_forced_confirm"] = True

        return prompt

    def _assess_ars(self, result: SafetyGateResult) -> dict:
        """P062 (2026-05-21): ARS 轻量论证评估。

        对每个拦截项标注 Acceptability / Relevance / Sufficiency。
        来源：CP-126 论证评估体系与元认知。

        Returns:
            {
                "A": {"pass": bool, "reason": str},
                "R": {"pass": bool, "reason": str},
                "S": {"pass": bool, "reason": str},
                "all_failed": bool,       # 三项全不通过 → 追加强制确认
                "prompt_injection": str,  # 注入到 AskQuestion 提示的文本
            }
        """
        # A: Acceptability — 前提可接受吗？
        #    检查匹配的正则是否存在已知误报模式
        a_pass = True
        a_reason = "正则匹配模式是已知的高风险操作信号，前提可接受"
        # 若匹配了多个模式 → 前提更可信
        if len(result.matched_patterns) >= 3:
            a_pass = True
            a_reason = f"多个独立模式（{len(result.matched_patterns)}个）同时匹配，前提高度可信"

        # R: Relevance — 匹配模式确实对应危险操作吗？
        r_pass = True
        r_reason = f"匹配的模式（{result.risk_type}）确实属于危险操作类别，理由相关"
        # 若唯一的匹配来自过于宽泛的正则 → 相关性降级
        too_broad = ["rm\\s+.*\\s+/[a-z]", "C:\\\\\\\\"]
        if any(bp in str(p) for bp in too_broad for p in result.matched_patterns):
            r_pass = False
            r_reason = "匹配的模式过于宽泛，可能包含误报——理由相关性不足"

        # S: Sufficiency — 证据充分吗？
        s_pass = len(result.matched_patterns) >= 2
        if s_pass:
            s_reason = f"{len(result.matched_patterns)} 条模式同时命中，证据充分"
        else:
            s_reason = f"仅 {len(result.matched_patterns)} 条模式命中，证据可能不足——建议预览命令输出后再判决"

        all_failed = not a_pass and not r_pass and not s_pass

        prompt_parts = [
            "\n【ARS 论证质量评估（CP-126）】",
            f"A·可接受性（前提是否可信？）：{'✅' if a_pass else '⚠️'} {a_reason}",
            f"R·相关性（匹配是否对应危险？）：{'✅' if r_pass else '⚠️'} {r_reason}",
            f"S·充分性（证据是否足够？）：{'✅' if s_pass else '⚠️'} {s_reason}",
        ]
        if all_failed:
            prompt_parts.append("⚠ ARS 三重不通过 — 拦截前提/相关性/充分性均有问题，建议用户仔细审视后再决定")

        return {
            "A": {"pass": a_pass, "reason": a_reason},
            "R": {"pass": r_pass, "reason": r_reason},
            "S": {"pass": s_pass, "reason": s_reason},
            "all_failed": all_failed,
            "prompt_injection": "\n".join(prompt_parts),
        }

    # ── Private helpers ───────────────────────────────────────

    def _is_windows(self) -> bool:
        return os.name == "nt"

    def _is_trash_safe(self, command: str) -> bool:
        """Check if command targets .trash/ and is non-recursive."""
        return bool(self._TRASH_SAFE_PATTERN.search(command))

    def _is_recursive_with_path(self, command: str) -> bool:
        """Check if the recursive delete also includes a file path pattern (still risky)."""
        # If .trash is mentioned with a wildcard, still risky
        return bool(re.search(r"\.trash[/\\][*?]", command, re.IGNORECASE))

    def _is_git_safe(self, command: str) -> bool:
        """Check if git command falls under safe staging-area operations."""
        return any(pat.search(command) for pat in self._GIT_SAFE_PATTERNS)

    def _extract_target_path(self, command: str) -> str:
        """Extract the likely target path from a command string."""
        # Simple heuristic: find last quoted path or space-separated path
        # First try quoted paths
        quoted = re.findall(r'"([^"]+)"', command)
        if quoted:
            return quoted[-1]

        # Then try drive-letter paths
        drive_path = re.findall(r"[A-Za-z]:\\[^\s]*", command)
        if drive_path:
            return drive_path[-1]

        # Fallback: last space-separated arg that looks like a path
        parts = command.split()
        for part in reversed(parts):
            if not part.startswith("-") and (
                "/" in part or "\\" in part or "." in part
            ):
                return part
        return "unknown"

    def _extract_process_name(self, command: str) -> str:
        """Extract the process name from a kill command."""
        # Windows: taskkill /f /im <name>
        m = re.search(r"taskkill\s+/f\s+/im\s+(\S+)", command, re.IGNORECASE)
        if m:
            return m.group(1)

        # Linux: killall <name> / pkill <name>
        m = re.search(r"(?:killall|pkill)\s+(\S+)", command, re.IGNORECASE)
        if m:
            return m.group(1)

        # PowerShell: Stop-Process -Name <name>
        m = re.search(r"Stop-Process\s+-Name\s+(\S+)", command, re.IGNORECASE)
        if m:
            return m.group(1)

        return "unknown"


# ── Module-level convenience ───────────────────────────────────────

gate = SafetyGate()
