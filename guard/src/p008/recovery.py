"""Interruption Recovery & Degradation Engine.

Guard MVP v0.3+. Handles four failure modes:

1. **Interruption Recovery**     — process crash → load state → resume or restart
2. **Degradation Matrix**        — LLM API down → deterministic-only mode
3. **Cold Start**                — no history → default L1 + empty logs
4. **Device Switch Detection**   — fingerprint changed → reset env state, keep FSM+KB

All decisions are deterministic — zero LLM dependency.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional


# ── Enums ──────────────────────────────────────────────────────────

class DegradationTier(str, Enum):
    """Which tier the system is currently running in."""
    FULL = "full"                  # All modules operational
    DETERMINISTIC = "deterministic"  # LLM API unavailable → skip LLM#1/#2/#3
    SAFETY_ONLY = "safety_only"    # Only safety_gate + state persistence
    UNAVAILABLE = "unavailable"    # Nothing working → fallback L1 + .mdc rules


class RecoveryAction(str, Enum):
    """What to do on restart."""
    RESUME = "resume"              # Continue from last known state
    RESTART = "restart"            # Start fresh, discard partial state
    RETRY_INTERRUPTED = "retry_interrupted"  # Re-attempt the interrupted task
    ASK_USER = "ask_user"          # Can't decide — ask the user


# ── Data structures ────────────────────────────────────────────────

@dataclass
class DeviceFingerprint:
    """Lightweight device identity for switch detection."""
    hostname: str = ""
    os: str = ""
    machine: str = ""
    workspace_root: str = ""
    python_version: str = ""


@dataclass
class RecoveryContext:
    """Full context needed to make a recovery decision."""

    state_exists: bool = False
    last_status: str = ""                 # from AgentState
    last_updated: str = ""
    consecutive_failures: int = 0

    # Device state
    device_fingerprint: DeviceFingerprint = field(default_factory=DeviceFingerprint)
    previous_fingerprint: DeviceFingerprint = field(default_factory=DeviceFingerprint)
    device_switched: bool = False

    # Module availability
    llm_api_available: bool = True
    safety_gate_available: bool = True
    state_persistence_available: bool = True

    # Degradation
    current_tier: str = DegradationTier.FULL.value

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RecoveryDecision:
    """Decision from the recovery engine."""

    action: str = RecoveryAction.ASK_USER.value
    degradation_tier: str = DegradationTier.FULL.value
    p008_default_level: int = 1
    reset_env_state: bool = False
    keep_fsm_history: bool = True
    keep_kb_counts: bool = True
    messages: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ── Recovery Engine ────────────────────────────────────────────────

class RecoveryEngine:
    """Deterministic recovery decision-making.

    Evaluates the current system state (state file, device fingerprint,
    module availability) and produces a RecoveryDecision without any LLM call.

    Usage:
        engine = RecoveryEngine("guard-state.json")
        decision = engine.decide(llm_api_available=True)
        if decision.action == RecoveryAction.RESUME:
            state = StatePersistence("guard-state.json").load()
            # continue from state.task.current_step
    """

    MAX_CONSECUTIVE_FAILURES = 3       # after this, force RESTART
    STATE_STALE_SECONDS = 86400        # 24 hours — state too old to resume

    def __init__(
        self,
        state_file: str | Path,
        fingerprint_file: str | Path | None = None,
    ) -> None:
        self.state_file = Path(state_file)
        self.fingerprint_file = (
            Path(fingerprint_file) if fingerprint_file
            else self.state_file.parent / "device-fingerprint.json"
        )

    # ── Public API ────────────────────────────────────────────

    def decide(
        self,
        llm_api_available: bool = True,
        safety_gate_available: bool = True,
    ) -> RecoveryDecision:
        """Make a recovery decision based on current system state.

        Args:
            llm_api_available: Is the LLM API reachable?
            safety_gate_available: Is safety_gate.py importable?

        Returns:
            RecoveryDecision with action, tier, and instructions.
        """
        ctx = self._build_context(llm_api_available, safety_gate_available)
        decision = RecoveryDecision()

        # ═══════════════════════════════════════════════════
        # Step 1: Determine degradation tier
        # ═══════════════════════════════════════════════════
        decision.degradation_tier = self._determine_tier(ctx)

        if decision.degradation_tier == DegradationTier.UNAVAILABLE.value:
            decision.action = RecoveryAction.RESTART.value
            decision.messages.append("Guard is completely unavailable — falling back to .mdc rules with default L1")
            decision.p008_default_level = 1
            return decision

        if decision.degradation_tier == DegradationTier.SAFETY_ONLY.value:
            decision.p008_default_level = 1
            decision.messages.append("Only safety gate operational — L1 default, no context injection")
            # If there's a state file, still try to resume interrupted task
            if ctx.state_exists and ctx.last_status == "interrupted":
                decision.action = RecoveryAction.RETRY_INTERRUPTED.value
                decision.messages.append("Interrupted task detected — retrying in safety-only mode")
            else:
                decision.action = RecoveryAction.RESTART.value
            return decision

        # ═══════════════════════════════════════════════════
        # Step 2: Device switch detection
        # ═══════════════════════════════════════════════════
        if ctx.device_switched:
            decision.reset_env_state = True
            decision.keep_fsm_history = True
            decision.keep_kb_counts = True
            decision.messages.append(
                "Device switch detected — resetting environment state "
                "(workspace path, device info) but keeping FSM history and KB validation counts"
            )

        # ═══════════════════════════════════════════════════
        # Step 3: Interruption recovery
        # ═══════════════════════════════════════════════════
        if not ctx.state_exists:
            # Cold start
            decision.action = RecoveryAction.RESTART.value
            decision.p008_default_level = 1
            decision.messages.append("Cold start: no previous state — defaulting to L1")
            return decision

        # State exists — check staleness
        if self._is_state_stale(ctx):
            decision.action = RecoveryAction.ASK_USER.value
            decision.messages.append(
                f"Previous state is stale (last updated: {ctx.last_updated}). "
                f"Recommend RESTART."
            )
            decision.notes.append("State older than 24 hours — likely irrelevant")
            return decision

        # Check status
        if ctx.last_status in ("interrupted", "executing", "classifying", "decomposing"):
            if ctx.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                decision.action = RecoveryAction.RESTART.value
                decision.messages.append(
                    f"Too many consecutive failures ({ctx.consecutive_failures}) — "
                    f"restarting fresh"
                )
            else:
                decision.action = RecoveryAction.RESUME.value
                decision.messages.append(
                    f"Resuming from {ctx.last_status} (failure count: {ctx.consecutive_failures})"
                )
        elif ctx.last_status == "completed":
            decision.action = RecoveryAction.RESTART.value
            decision.messages.append("Previous task completed — starting fresh")
        elif ctx.last_status == "failed":
            decision.action = RecoveryAction.RETRY_INTERRUPTED.value
            decision.messages.append("Previous task failed — offering retry")
        else:
            # idle or unknown
            decision.action = RecoveryAction.RESTART.value
            decision.messages.append(f"Idle state detected — starting fresh")

        return decision

    def save_fingerprint(self, fingerprint: Optional[DeviceFingerprint] = None) -> None:
        """Save current device fingerprint for future switch detection."""
        if fingerprint is None:
            fingerprint = self._collect_fingerprint()
        self.fingerprint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.fingerprint_file, "w", encoding="utf-8") as f:
            json.dump(asdict(fingerprint), f, ensure_ascii=False, indent=2)

    def check_device_switch(self) -> bool:
        """Check if the device has changed since last fingerprint save."""
        if not self.fingerprint_file.exists():
            return False

        try:
            with open(self.fingerprint_file, "r", encoding="utf-8") as f:
                prev = json.load(f)
        except (json.JSONDecodeError, OSError):
            return False

        current = self._collect_fingerprint()
        # Compare key fields (ignore minor version changes)
        return (
            prev.get("hostname") != current.hostname
            or prev.get("os") != current.os
            or prev.get("workspace_root") != current.workspace_root
        )

    # ── Internal ─────────────────────────────────────────────

    def _build_context(
        self, llm_api_available: bool, safety_gate_available: bool
    ) -> RecoveryContext:
        """Assemble the full recovery context."""
        ctx = RecoveryContext(
            llm_api_available=llm_api_available,
            safety_gate_available=safety_gate_available,
            state_persistence_available=True,
        )

        # Load state file
        ctx.state_exists = self.state_file.exists()
        if ctx.state_exists:
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state_data = json.load(f)
                ctx.last_status = state_data.get("status", "")
                ctx.last_updated = state_data.get("updated_at", "")
                ctx.consecutive_failures = state_data.get("consecutive_failures", 0)
            except (json.JSONDecodeError, OSError):
                ctx.state_exists = False

        # Device fingerprint
        ctx.previous_fingerprint = self._load_fingerprint()
        ctx.device_fingerprint = self._collect_fingerprint()
        ctx.device_switched = self._has_device_switched(
            ctx.previous_fingerprint, ctx.device_fingerprint
        )

        return ctx

    @staticmethod
    def _determine_tier(ctx: RecoveryContext) -> str:
        """Determine which degradation tier the system is in."""
        # LLM API down → deterministic
        if not ctx.llm_api_available:
            if ctx.safety_gate_available:
                return DegradationTier.DETERMINISTIC.value
            else:
                return DegradationTier.SAFETY_ONLY.value

        # All good
        if ctx.safety_gate_available and ctx.llm_api_available:
            return DegradationTier.FULL.value

        # Only safety gate
        if ctx.safety_gate_available:
            return DegradationTier.SAFETY_ONLY.value

        return DegradationTier.UNAVAILABLE.value

    @staticmethod
    def _is_state_stale(ctx: RecoveryContext) -> bool:
        """Check if the last state update is too old to resume from."""
        if not ctx.last_updated:
            return True
        try:
            # Parse ISO timestamp
            from datetime import datetime
            updated_dt = datetime.strptime(ctx.last_updated[:19], "%Y-%m-%dT%H:%M:%S")
            updated_ts = updated_dt.timestamp()
            now_ts = time.time()
            return (now_ts - updated_ts) > RecoveryEngine.STATE_STALE_SECONDS
        except (ValueError, OSError):
            return True

    def _collect_fingerprint(self) -> DeviceFingerprint:
        """Collect current device fingerprint."""
        import platform
        import os
        return DeviceFingerprint(
            hostname=platform.node(),
            os=platform.system(),
            machine=platform.machine(),
            workspace_root=os.environ.get("CURSOR_PROJECT_DIR", str(Path.cwd())),
            python_version=platform.python_version(),
        )

    def _load_fingerprint(self) -> DeviceFingerprint:
        """Load previously saved fingerprint."""
        if not self.fingerprint_file.exists():
            return DeviceFingerprint()
        try:
            with open(self.fingerprint_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return DeviceFingerprint(**data)
        except (json.JSONDecodeError, OSError, TypeError):
            return DeviceFingerprint()

    @staticmethod
    def _has_device_switched(
        prev: DeviceFingerprint, curr: DeviceFingerprint
    ) -> bool:
        """Detect meaningful device switch."""
        if not prev.hostname:
            return False  # No previous fingerprint → not a switch
        return (
            prev.hostname != curr.hostname
            or prev.os != curr.os
            or prev.workspace_root != curr.workspace_root
        )


# ── Degradation Mode Selector ─────────────────────────────────────

def apply_degradation(
    tier: str,
    p008_default_level: int = 1,
) -> dict:
    """Apply degradation tier settings.

    Returns a dict that can be injected into the Guard pipeline to
    selectively enable/disable modules based on the current tier.

    Args:
        tier: One of "full", "deterministic", "safety_only", "unavailable"
        p008_default_level: Default L level when P008 is unavailable

    Returns:
        {
            "enable_llm1": bool,
            "enable_llm2": bool,
            "enable_llm3": bool,
            "enable_safety_gate": bool,
            "enable_kb_injection": bool,
            "enable_tool_selection": bool,
            "enable_feedback": bool,
            "p008_default_level": int,
            "notes": [...],
        }
    """
    config = {
        "enable_llm1": False,
        "enable_llm2": False,
        "enable_llm3": False,
        "enable_safety_gate": False,
        "enable_kb_injection": False,
        "enable_tool_selection": False,
        "enable_feedback": False,
        "p008_default_level": p008_default_level,
        "notes": [],
    }

    if tier == DegradationTier.FULL.value:
        config["enable_llm1"] = True
        config["enable_llm2"] = True
        config["enable_llm3"] = True
        config["enable_safety_gate"] = True
        config["enable_kb_injection"] = True
        config["enable_tool_selection"] = True
        config["enable_feedback"] = True
        config["notes"].append("Full Guard operational — all modules enabled")

    elif tier == DegradationTier.DETERMINISTIC.value:
        # LLM API down → skip LLM#1/#2/#3, keep everything else
        config["enable_safety_gate"] = True
        config["enable_kb_injection"] = False  # no LLM to inject into
        config["enable_tool_selection"] = True
        config["enable_feedback"] = True
        config["notes"].append(
            "LLM API unavailable — running in deterministic mode. "
            "P008 evaluation, safety gate, tool selection, and feedback remain active. "
            "Context injection (LLM#1/#2/#3) and KB mounting are disabled."
        )

    elif tier == DegradationTier.SAFETY_ONLY.value:
        config["enable_safety_gate"] = True
        config["notes"].append(
            "Safety-only mode — only safety gate and state persistence active. "
            f"Default P008 level: L{config['p008_default_level']}."
        )

    elif tier == DegradationTier.UNAVAILABLE.value:
        config["notes"].append(
            "Guard completely unavailable — all decisions fall back to .mdc rules. "
            f"Default P008 level: L{config['p008_default_level']}."
        )

    return config
