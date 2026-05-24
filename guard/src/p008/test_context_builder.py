"""Unit tests for injection engine (P032).

Covers: TemplateRegistry, ContextBuilder (LLM#1, LLM#2, LLM#3),
        estimate_duration, compute_anti_bias_directives
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from p008.context_builder import (
    ContextBuilder,
    TemplateRegistry,
    TaskTemplate,
    estimate_duration,
    compute_anti_bias_directives,
    InjectionContext,
)


def run_tests() -> int:
    failures = 0

    # ═════════════════════════════════════════════════════════
    # 1. TemplateRegistry
    # ═════════════════════════════════════════════════════════

    reg = TemplateRegistry()

    desc = "1a. Default templates registered"
    all_tpls = reg.list_all()
    if len(all_tpls) < 8:
        failures += 1
        print(f"  FAIL: {desc}: only {len(all_tpls)} templates")
    else:
        print(f"  PASS: {desc} — {len(all_tpls)} templates")

    desc = "1b. get() by template_id"
    tpl = reg.get("tpl_notion_create")
    if tpl is None or tpl.task_type != "notion_create":
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "1c. get_by_task_type()"
    tpl = reg.get_by_task_type("code_generate")
    if tpl is None or tpl.template_id != "tpl_code_generate":
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "1d. register() new template"
    new_tpl = TaskTemplate("tpl_custom", "custom_task", "A custom task")
    reg.register(new_tpl)
    tpl = reg.get("tpl_custom")
    if tpl is None:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "1e. get() for missing template returns None"
    tpl = reg.get("nonexistent")
    if tpl is not None:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    # ═════════════════════════════════════════════════════════
    # 2. estimate_duration
    # ═════════════════════════════════════════════════════════

    desc = "2a. estimate_duration without history returns default ±50%"
    est, guidance = estimate_duration("unknown_task")
    if est != 600 or "±50%" not in guidance:
        failures += 1
        print(f"  FAIL: {desc}: est={est}, guidance='{guidance[:80]}'")
    else:
        print(f"  PASS: {desc} — {est}s, {guidance[:60]}...")

    desc = "2b. estimate_duration with history returns P80"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        for dur in [100, 150, 200, 300, 500, 600, 700, 800, 900, 1200]:
            f.write(json.dumps({"task_type": "test_task", "actual_duration_s": dur}) + "\n")
        log_path = Path(f.name)

    est, guidance = estimate_duration("test_task", decision_log_path=log_path)
    # Sorted: [100,150,200,300,500,600,700,800,900,1200] → P80 index = 8 → 900
    if est != 900:
        failures += 1
        print(f"  FAIL: {desc}: expected P80=900, got {est}")
    else:
        print(f"  PASS: {desc} — P80={est}s")
    log_path.unlink()

    desc = "2c. estimate_duration ignores non-matching task_types"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        f.write(json.dumps({"task_type": "other_task", "actual_duration_s": 999}) + "\n")
        log_path = Path(f.name)
    est, guidance = estimate_duration("test_task", decision_log_path=log_path)
    if est != 600:  # no matching entries → default
        failures += 1
        print(f"  FAIL: {desc}: expected 600, got {est}")
    else:
        print(f"  PASS: {desc}")
    log_path.unlink()

    # ═════════════════════════════════════════════════════════
    # 3. compute_anti_bias_directives
    # ═════════════════════════════════════════════════════════

    desc = "3a. No overlap → not biased"
    result = compute_anti_bias_directives(
        current_kb_top_results=["CP-098", "CP-099", "CP-100"],
        last_round_active_protocols=["CP-020", "CP-057"],
    )
    if result["biased"]:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "3b. 2 overlaps → biased (threshold=2)"
    result = compute_anti_bias_directives(
        current_kb_top_results=["CP-020", "CP-057", "CP-098"],
        last_round_active_protocols=["CP-020", "CP-057"],
    )
    if not result["biased"] or len(result["directives"]) == 0:
        failures += 1
        print(f"  FAIL: {desc}: biased={result['biased']}, directives={result['directives']}")
    else:
        print(f"  PASS: {desc} — {len(result['directives'])} directive(s)")

    desc = "3c. 1 overlap → not biased (below threshold=2)"
    result = compute_anti_bias_directives(
        current_kb_top_results=["CP-020", "CP-098", "CP-099"],
        last_round_active_protocols=["CP-020", "CP-057"],
    )
    if result["biased"]:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "3d. Biased result includes downweighted map"
    result = compute_anti_bias_directives(
        current_kb_top_results=["CP-020", "CP-057", "CP-098"],
        last_round_active_protocols=["CP-020", "CP-057"],
    )
    if "CP-020" not in result["downweighted"] or result["downweighted"]["CP-020"] != 0.7:
        failures += 1
        print(f"  FAIL: {desc}: {result['downweighted']}")
    else:
        print(f"  PASS: {desc}")

    # ═════════════════════════════════════════════════════════
    # 4. ContextBuilder — LLM#1
    # ═════════════════════════════════════════════════════════

    builder = ContextBuilder()

    desc = "4a. build_intent_context returns LLM#1 context"
    ctx = builder.build_intent_context("notion_create")
    if ctx.call_point != "LLM#1":
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "4b. LLM#1 context has output_schema"
    if ctx.output_schema is None or "task_type" not in str(ctx.output_schema):
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "4c. LLM#1 context has system_prompt"
    if not ctx.system_prompt:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "4d. LLM#1 context with alias map"
    alias_map = {"create": "notion_create", "delete": "notion_delete"}
    ctx = builder.build_intent_context("notion_create", alias_map=alias_map)
    if "Alias table" not in str(ctx.kb_frameworks):
        failures += 1
        print(f"  FAIL: {desc}: {ctx.kb_frameworks}")
    else:
        print(f"  PASS: {desc}")

    desc = "4e. LLM#1 context for unknown task type"
    ctx = builder.build_intent_context("nonexistent")
    if ctx.call_point != "LLM#1":
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    # ═════════════════════════════════════════════════════════
    # 5. ContextBuilder — LLM#2
    # ═════════════════════════════════════════════════════════

    desc = "5a. build_decompose_context returns LLM#2 context"
    ctx = builder.build_decompose_context("notion_create")
    if ctx.call_point != "LLM#2":
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "5b. LLM#2 context has duration guidance"
    if not ctx.duration_guidance:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc} — {ctx.duration_guidance[:50]}...")

    desc = "5c. LLM#2 context with KB protocols"
    ctx = builder.build_decompose_context(
        "notion_create", kb_protocols=["CP-020", "CP-057"]
    )
    if "CP-020" not in str(ctx.kb_frameworks):
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "5d. LLM#2 context with anti-bias when overlap ≥2"
    ctx = builder.build_decompose_context(
        "notion_create",
        kb_protocols=["CP-020", "CP-057", "CP-098"],
        last_round_protocols=["CP-020", "CP-057"],
    )
    if not ctx.anti_bias_directives:
        failures += 1
        print(f"  FAIL: {desc}: no anti_bias directives")
    else:
        print(f"  PASS: {desc} — {len(ctx.anti_bias_directives)} directive(s)")

    desc = "5e. LLM#2 context has decomposition output_schema"
    if ctx.output_schema is None or "steps" not in str(ctx.output_schema):
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    # ═════════════════════════════════════════════════════════
    # 6. ContextBuilder — LLM#3
    # ═════════════════════════════════════════════════════════

    desc = "6a. build_fill_context returns LLM#3 context"
    ctx = builder.build_fill_context("notion_create")
    if ctx.call_point != "LLM#3":
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "6b. LLM#3 context with slot_map"
    ctx = builder.build_fill_context(
        "notion_create",
        slot_map={"title": "Meeting Notes", "parent_page_id": "abc123"},
    )
    if "Meeting Notes" not in str(ctx.constraints):
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "6c. LLM#3 context with missing_fields"
    ctx = builder.build_fill_context(
        "notion_create",
        missing_fields=["target_date", "assignee"],
    )
    if "target_date" not in str(ctx.constraints):
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "6d. LLM#3 has 'do not guess' constraint"
    if "Do NOT guess" not in str(ctx.constraints):
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "6e. LLM#3 output_schema has user_questions"
    if ctx.output_schema is None or "user_questions" not in str(ctx.output_schema):
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    # ═════════════════════════════════════════════════════════
    # 7. InjectionContext.to_prompt_dict()
    # ═════════════════════════════════════════════════════════

    desc = "7a. to_prompt_dict produces valid dict"
    ctx = builder.build_intent_context("notion_create")
    d = ctx.to_prompt_dict()
    if "system" not in d or "task" not in d:
        failures += 1
        print(f"  FAIL: {desc}: {d.keys()}")
    else:
        print(f"  PASS: {desc}")

    desc = "7b. to_prompt_dict includes anti_bias when present"
    ctx = builder.build_decompose_context(
        "notion_create",
        kb_protocols=["CP-020", "CP-057", "CP-098"],
        last_round_protocols=["CP-020", "CP-057"],
    )
    d = ctx.to_prompt_dict()
    if "anti_bias" not in d:
        failures += 1
        print(f"  FAIL: {desc}: {d.keys()}")
    else:
        print(f"  PASS: {desc}")

    desc = "7c. to_prompt_dict includes duration_guidance when present"
    if "duration_guidance" not in d:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    # ── Summary ──
    print(f"\n{'='*50}")
    if failures == 0:
        print("  All injection engine tests PASSED")
    else:
        print(f"  {failures} test(s) FAILED")
    return failures


if __name__ == "__main__":
    sys.exit(run_tests())
