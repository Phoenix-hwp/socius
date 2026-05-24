"""Cross-device consistency test framework (P037).

Since real cross-device testing requires two physical machines, this module
provides a consistency test harness that:

1. Defines 5 standardized task scenarios
2. Runs the full Guard pipeline on each
3. Records metric snapshots
4. Provides a compare() function to diff two snapshots
5. Flags deviations >10%

The user runs this on Device A, copies snapshot-A.json to Device B,
runs on Device B, copies snapshot-B.json back, then calls compare().

Target: behavioral deviation < 10% across devices.
"""

from __future__ import annotations

import json
import sys
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # src/p008/ → src/ on path for `from p008.xxx import`

from p008.safety_gate import SafetyGate
from p008.constraint_applier import SchemaValidator
from p008.device_neutralizer import DeviceNeutralizer
from p008.tool_selector import ToolSelector
from p008.context_builder import ContextBuilder
from p008.state_persistence import ConsensusClassifier


# ── Standardized task scenarios ───────────────────────────────────

STANDARD_TASKS: list[dict] = [
    {
        "id": "T1-competitive-analysis",
        "description": "分析Notion竞品Airtable的功能差异",
        "expected_task_type": "kb_search",
        "category": "information_retrieval",
    },
    {
        "id": "T2-document-generation",
        "description": "写一份产品设计评审报告的Markdown文档",
        "expected_task_type": "code_generate",
        "category": "document_generation",
    },
    {
        "id": "T3-code-modification",
        "description": "修改safety_gate.py，增加对rmdir命令的检测正则",
        "expected_task_type": "code_generate",
        "category": "code_modification",
    },
    {
        "id": "T4-notion-create",
        "description": "在Notion中创建一个2026年Q2产品路线图页面",
        "expected_task_type": "notion_create",
        "category": "notion_operation",
    },
    {
        "id": "T5-proposal-comparison",
        "description": "对比在Skill执行前使用git stash vs git rev-parse方案的优劣",
        "expected_task_type": "kb_search",
        "category": "proposal_comparison",
    },
]


# ── Data structures ────────────────────────────────────────────────

@dataclass
class TaskSnapshot:
    """Single task execution snapshot."""
    task_id: str = ""
    device_id: str = ""
    task_type_classified: str = ""
    p008_level: int = 0
    consensus_level: float = 0.0
    output_medium: str = ""
    renderer: str = ""
    blocked: bool = False
    injection_hash: str = ""          # SHA256 of serialized injection context (strips device-specific fields)


@dataclass
class DeviceSnapshot:
    """Complete snapshot for one device."""
    device_id: str = ""
    hostname: str = ""
    os: str = ""
    workspace: str = ""
    timestamp: str = ""
    tasks: list[TaskSnapshot] = field(default_factory=list)


@dataclass
class ConsistencyReport:
    """Cross-device consistency comparison result."""
    device_a_id: str = ""
    device_b_id: str = ""
    task_count: int = 0
    exact_matches: int = 0
    deviations: list[dict] = field(default_factory=list)
    overall_consistency: float = 0.0     # fraction of fields that matched across all tasks
    recommendations: list[str] = field(default_factory=list)

    def is_acceptable(self, threshold: float = 0.90) -> bool:
        return self.overall_consistency >= threshold


# ── Consistency Test Harness ──────────────────────────────────────

class ConsistencyHarness:
    """Runs standardized tasks and produces device snapshots.

    Usage on Device A:
        harness = ConsistencyHarness(workspace_root="D:/Phoenix/cursor-knowledge")
        snapshot = harness.run_all_tasks(device_id="device-A")
        with open("snapshot-A.json", "w") as f:
            json.dump(snapshot.to_dict(), f, indent=2)

    Then on Device B:
        harness = ConsistencyHarness(workspace_root="C:/Users/x/cursor-knowledge")
        snapshot = harness.run_all_tasks(device_id="device-B")
        with open("snapshot-B.json", "w") as f:
            json.dump(snapshot.to_dict(), f, indent=2)

    Finally, compare:
        report = compare_snapshots(snapshot_A, snapshot_B)
        print(f"Consistency: {report.overall_consistency:.1%}")
    """

    def __init__(self, workspace_root: str = "") -> None:
        self.workspace = workspace_root or str(Path.cwd())
        self.dn = DeviceNeutralizer(workspace_root=self.workspace)

    def run_all_tasks(self, device_id: str = "device-A") -> DeviceSnapshot:
        """Run all standardized tasks and produce a snapshot."""
        import time
        import platform

        snapshot = DeviceSnapshot(
            device_id=device_id,
            hostname=platform.node(),
            os=platform.system(),
            workspace=self.workspace,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

        for task in STANDARD_TASKS:
            ts = self._run_single_task(task)
            ts.device_id = device_id
            snapshot.tasks.append(ts)

        return snapshot

    def _run_single_task(self, task: dict) -> TaskSnapshot:
        """Run a single task through the Guard pipeline and capture metrics."""
        ts = TaskSnapshot(task_id=task["id"])

        # Step 1: Classification (consensus)
        cc = ConsensusClassifier(known_task_types=[
            "notion_create", "notion_query", "notion_update", "notion_delete",
            "code_generate", "kb_search", "knowledge_digestion",
            "simulation", "system_audit", "conversation_management", "generic",
        ])
        # Import heuristics from guard.py (not in src/p008, but in repo root)
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
        from guard import _heuristic_classify, _heuristic_p008

        task_type = _heuristic_classify(task["description"])
        votes = [
            {"task_type": task_type, "p008_level": _heuristic_p008(task_type), "confidence": 0.85},
            {"task_type": task_type, "p008_level": _heuristic_p008(task_type), "confidence": 0.80},
            {"task_type": "generic", "p008_level": 0, "confidence": 0.40},
        ]
        consensus = cc.classify(votes)

        ts.task_type_classified = consensus.task_type
        ts.p008_level = consensus.p008_level
        ts.consensus_level = consensus.consensus_level

        # Step 2: Tool selection
        tselector = ToolSelector()
        tool_result = tselector.select(consensus.task_type)
        ts.output_medium = tool_result.output_medium
        ts.renderer = tool_result.selected_renderer.name if tool_result.selected_renderer else "none"
        ts.blocked = tool_result.blocked

        # Step 3: Injection context hash (strips device-specific fields)
        builder = ContextBuilder()
        ctx = builder.build_intent_context(consensus.task_type)
        neutral_prompt = ctx.to_prompt_dict()
        # Strip device-specific fields before hashing
        neutral_prompt.pop("duration_guidance", None)
        injection_json = json.dumps(neutral_prompt, sort_keys=True, ensure_ascii=True)
        ts.injection_hash = hashlib.sha256(injection_json.encode()).hexdigest()[:16]

        return ts


# ── Comparison Logic ───────────────────────────────────────────────

def compare_snapshots(snapshot_a: DeviceSnapshot, snapshot_b: DeviceSnapshot) -> ConsistencyReport:
    """Compare two device snapshots and produce a consistency report.

    Fields compared:
        - task_type_classified (string equality)
        - p008_level (exact match)
        - output_medium (string equality)
        - renderer (string equality)
        - blocked (boolean equality)
        - injection_hash (exact match)

    Returns ConsistencyReport with overall consistency and deviation list.
    """
    report = ConsistencyReport(
        device_a_id=snapshot_a.device_id,
        device_b_id=snapshot_b.device_id,
        task_count=len(STANDARD_TASKS),
    )

    if len(snapshot_a.tasks) != len(snapshot_b.tasks):
        report.recommendations.append(
            f"Task count mismatch: A={len(snapshot_a.tasks)}, B={len(snapshot_b.tasks)}"
        )
        return report

    total_checks = 0
    total_passed = 0

    for ta, tb in zip(snapshot_a.tasks, snapshot_b.tasks):
        task_deviations = []
        checks = [
            ("task_type", ta.task_type_classified, tb.task_type_classified),
            ("p008_level", ta.p008_level, tb.p008_level),
            ("output_medium", ta.output_medium, tb.output_medium),
            ("renderer", ta.renderer, tb.renderer),
            ("blocked", ta.blocked, tb.blocked),
            ("injection_hash", ta.injection_hash, tb.injection_hash),
        ]

        for field, val_a, val_b in checks:
            total_checks += 1
            if val_a == val_b:
                total_passed += 1
            else:
                task_deviations.append({
                    "field": field,
                    "device_a": str(val_a),
                    "device_b": str(val_b),
                })

        if task_deviations:
            report.deviations.append({
                "task_id": ta.task_id,
                "expected_task_type": STANDARD_TASKS[len(report.deviations)]["expected_task_type"] if len(report.deviations) < len(STANDARD_TASKS) else "",
                "deviations": task_deviations,
            })

    report.exact_matches = report.task_count - len(report.deviations)
    report.overall_consistency = total_passed / total_checks if total_checks > 0 else 0.0

    # Generate recommendations
    if report.overall_consistency < 0.90:
        report.recommendations.append(
            f"Overall consistency {report.overall_consistency:.1%} below 90% threshold — "
            f"review {len(report.deviations)} task(s) with deviations."
        )

    # Specific field-level recommendations
    task_type_devs = sum(
        1 for d in report.deviations for fd in d["deviations"] if fd["field"] == "task_type"
    )
    if task_type_devs > 0:
        report.recommendations.append(
            f"Task type classification differed in {task_type_devs} fields — "
            f"review heuristic classification keywords for cross-device consistency."
        )

    injection_hash_devs = sum(
        1 for d in report.deviations for fd in d["deviations"] if fd["field"] == "injection_hash"
    )
    if injection_hash_devs > 0:
        report.recommendations.append(
            f"Injection context differed in {injection_hash_devs} tasks — "
            f"check device_neutralizer for residual device-specific fields in prompts."
        )

    return report


# ── CLI entry point ────────────────────────────────────────────────

def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Cross-device Guard consistency test")
    parser.add_argument("action", choices=["snapshot", "compare"], help="Action to perform")
    parser.add_argument("--device-id", default="device-A", help="Device identifier for snapshot")
    parser.add_argument("--workspace", default="", help="Workspace root path")
    parser.add_argument("--snapshot-a", help="Path to Device A snapshot JSON")
    parser.add_argument("--snapshot-b", help="Path to Device B snapshot JSON")
    args = parser.parse_args()

    if args.action == "snapshot":
        harness = ConsistencyHarness(workspace_root=args.workspace)
        snapshot = harness.run_all_tasks(device_id=args.device_id)
        print(json.dumps(snapshot.__dict__, default=lambda o: o.__dict__ if hasattr(o, '__dict__') else str(o), ensure_ascii=False, indent=2))
        return 0

    elif args.action == "compare":
        if not args.snapshot_a or not args.snapshot_b:
            print("Error: --snapshot-a and --snapshot-b required for compare action")
            return 1

        with open(args.snapshot_a, "r", encoding="utf-8") as f:
            data_a = json.load(f)
        with open(args.snapshot_b, "r", encoding="utf-8") as f:
            data_b = json.load(f)

        # Reconstruct snapshots from dicts
        sna = DeviceSnapshot(
            device_id=data_a.get("device_id", ""),
            hostname=data_a.get("hostname", ""),
            os=data_a.get("os", ""),
            workspace=data_a.get("workspace", ""),
            timestamp=data_a.get("timestamp", ""),
            tasks=[TaskSnapshot(**t) for t in data_a.get("tasks", [])],
        )
        snb = DeviceSnapshot(
            device_id=data_b.get("device_id", ""),
            hostname=data_b.get("hostname", ""),
            os=data_b.get("os", ""),
            workspace=data_b.get("workspace", ""),
            timestamp=data_b.get("timestamp", ""),
            tasks=[TaskSnapshot(**t) for t in data_b.get("tasks", [])],
        )

        report = compare_snapshots(sna, snb)
        print(f"Consistency: {report.overall_consistency:.1%}")
        print(f"Exact matches: {report.exact_matches}/{report.task_count}")
        if report.deviations:
            print(f"Deviations:")
            for d in report.deviations:
                print(f"  {d['task_id']}:")
                for fd in d['deviations']:
                    print(f"    {fd['field']}: A={fd['device_a']} vs B={fd['device_b']}")
        if report.recommendations:
            print(f"Recommendations:")
            for r in report.recommendations:
                print(f"  - {r}")
        print(f"Acceptable (≥90%): {report.is_acceptable()}")

        return 0 if report.is_acceptable() else 1


if __name__ == "__main__":
    sys.exit(main())
