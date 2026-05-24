"""P008 Decision Engine & Guard System.

P008 Core (decision scoring):
    dimensions.py       — dimension enums, R/C track mapping tables, KB downgrade
    engine.py           — P008Engine: score all 7 dims → aggregate L_R, L_C → L_final
    p008_result.py      — P008Result dataclass
    decision_log.py     — Decision-Log.jsonl append/query
    fsm.py              — Finite state machine: auto-upgrade/downgrade
    cli.py              — CLI entry: JSON input → JSON output

Guard MVP (runtime enforcement, v0.3):
    safety_gate.py       — High-risk command interception (matches flow-high-risk-safety.mdc patterns)
    constraint_applier.py — SchemaValidator + FrameworkConstraintInjector
    device_neutralizer.py — Cross-device path normalization (D:\\ → ~/workspace/)
    tool_selector.py      — Three-layer tool/renderer selection with degradation
    context_builder.py    — Multi-stage LLM context injection (planning fallacy, anti-bias)
    feedback.py           — Zero-LLM objective execution feedback + duration logging
    kb_validator.py       — KB protocol step-level validation
    tool_reliability.py   — Tool invocation reliability tracking
    state_persistence.py  — Agent session state save/load
    recovery.py           — Interruption recovery engine + degradation strategies
    cross_device.py       — Cross-device consistency testing harness
    annotate_guard_replaceable.py — Batch annotation of guard_replaceable in .mdc rules

CLI:
    guard.py (repo root)  — Guard CLI entry (--status, --check-command, task pipeline)
"""

# P008 Core
from .engine import P008Engine
from .p008_result import P008Result
from .decision_log import DecisionEntry, read_entries, append_entry, DEFAULT_LOG_PATH
from .fsm import FSMQueryArgs, query_fsm_state, compute_T_penalty, run_premortem_check

# Guard MVP
from .safety_gate import SafetyGate, SafetyGateResult
from .constraint_applier import SchemaValidator, FrameworkConstraintInjector
from .device_neutralizer import DeviceNeutralizer
from .tool_selector import ToolSelector
from .context_builder import ContextBuilder, InjectionContext
from .feedback import ObjectiveFeedback, SignalCollector, ExecutionSignal, ObjectiveAssessment
from .kb_validator import KBValidator
from .tool_reliability import ToolReliabilityTracker
from .state_persistence import StatePersistence, ConsensusClassifier
from .recovery import RecoveryEngine
from .cross_device import ConsistencyHarness

__all__ = [
    # P008 Core
    "P008Engine",
    "P008Result",
    "DecisionEntry",
    "read_entries",
    "append_entry",
    "DEFAULT_LOG_PATH",
    "FSMQueryArgs",
    "query_fsm_state",
    "compute_T_penalty",
    "run_premortem_check",
    # Guard MVP
    "SafetyGate",
    "SafetyGateResult",
    "SchemaValidator",
    "FrameworkConstraintInjector",
    "DeviceNeutralizer",
    "ToolSelector",
    "ContextBuilder",
    "InjectionContext",
    "ObjectiveFeedback",
    "SignalCollector",
    "ExecutionSignal",
    "ObjectiveAssessment",
    "KBValidator",
    "ToolReliabilityTracker",
    "StatePersistence",
    "ConsensusClassifier",
    "RecoveryEngine",
    "ConsistencyHarness",
]
