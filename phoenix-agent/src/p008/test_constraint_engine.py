"""Unit tests for Guard MVP v0.2 constraint engine modules.

Covers: constraint_applier, device_neutralizer, tool_selector
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from p008.constraint_applier import (
    SchemaValidator,
    SchemaValidationResult,
    FrameworkConstraintInjector,
    FrameworkConstraint,
)
from p008.device_neutralizer import DeviceNeutralizer
from p008.tool_selector import (
    ToolSelector,
    ToolSelectionResult,
    TaskCapability,
    Renderer,
)


def run_tests() -> int:
    failures = 0

    # ═════════════════════════════════════════════════════════
    # 1. SchemaValidator
    # ═════════════════════════════════════════════════════════

    sv = SchemaValidator()

    # 1a. Basic object validation — valid
    schema = {
        "type": "object",
        "required": ["name", "age"],
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0, "maximum": 150},
        },
    }
    data = {"name": "Alice", "age": 30}
    result = sv.validate(data, schema)
    desc = "1a. Valid object passes"
    if not result.valid:
        failures += 1
        print(f"  FAIL: {desc}: {result.errors}")
    else:
        print(f"  PASS: {desc}")

    # 1b. Missing required field
    data = {"name": "Bob"}
    result = sv.validate(data, schema)
    desc = "1b. Missing required field detected"
    if result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc} — {len(result.errors)} error(s)")

    # 1c. Wrong type
    data = {"name": "Carol", "age": "thirty"}
    result = sv.validate(data, schema)
    desc = "1c. Wrong type detected"
    if result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    # 1d. Value out of range (minimum)
    data = {"name": "Dave", "age": -5}
    result = sv.validate(data, schema)
    desc = "1d. Value out of range (minimum) detected"
    if result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    # 1e. Value out of range (maximum)
    data = {"name": "Eve", "age": 200}
    result = sv.validate(data, schema)
    desc = "1e. Value out of range (maximum) detected"
    if result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    # 1f. Enum validation
    schema_enum = {
        "type": "object",
        "required": ["status"],
        "properties": {"status": {"type": "string", "enum": ["active", "inactive", "deleted"]}},
    }
    result = sv.validate({"status": "active"}, schema_enum)
    desc = "1f. Enum value in set passes"
    if not result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    result = sv.validate({"status": "unknown"}, schema_enum)
    desc = "1g. Enum value not in set detected"
    if result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    # 1h. Const value
    schema_const = {"type": "object", "required": ["version"], "properties": {"version": {"const": "1.0"}}}
    result = sv.validate({"version": "1.0"}, schema_const)
    desc = "1h. Const value matches passes"
    if not result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    result = sv.validate({"version": "2.0"}, schema_const)
    desc = "1i. Const value mismatch detected"
    if result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    # 1j. String pattern
    schema_pattern = {"type": "object", "required": ["email"], "properties": {"email": {"type": "string", "pattern": r".+@.+\..+"}}}
    result = sv.validate({"email": "user@example.com"}, schema_pattern)
    desc = "1j. String pattern match passes"
    if not result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    result = sv.validate({"email": "not-an-email"}, schema_pattern)
    desc = "1k. String pattern mismatch detected"
    if result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    # 1l. String minLength / maxLength
    schema_len = {"type": "object", "required": ["code"], "properties": {"code": {"type": "string", "minLength": 3, "maxLength": 6}}}
    result = sv.validate({"code": "abc"}, schema_len)
    desc = "1l. String minLength met passes"
    if not result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    result = sv.validate({"code": "ab"}, schema_len)
    desc = "1m. String minLength violation detected"
    if result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    result = sv.validate({"code": "abcdefg"}, schema_len)
    desc = "1n. String maxLength violation detected"
    if result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    # 1o. Array validation
    schema_array = {
        "type": "object",
        "required": ["items"],
        "properties": {"items": {"type": "array", "items": {"type": "string"}}},
    }
    result = sv.validate({"items": ["a", "b", "c"]}, schema_array)
    desc = "1o. Array with correct item types passes"
    if not result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    result = sv.validate({"items": ["a", 1, "c"]}, schema_array)
    desc = "1p. Array with wrong item type detected"
    if result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    # 1q. Additional properties blocked
    schema_no_extra = {
        "type": "object",
        "required": ["name"],
        "properties": {"name": {"type": "string"}},
        "additionalProperties": False,
    }
    result = sv.validate({"name": "test", "extra": "should_fail"}, schema_no_extra)
    desc = "1q. Additional property blocked"
    if result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    # 1r. JSON string validation
    result = sv.validate_json_string('{"name": "test"}', schema_no_extra)
    desc = "1r. JSON string valid object passes"
    if not result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    result = sv.validate_json_string('not json', schema_no_extra)
    desc = "1s. Invalid JSON string detected"
    if result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    # 1t. Nested object validation
    schema_nested = {
        "type": "object",
        "required": ["user"],
        "properties": {
            "user": {
                "type": "object",
                "required": ["name", "address"],
                "properties": {
                    "name": {"type": "string"},
                    "address": {
                        "type": "object",
                        "required": ["city"],
                        "properties": {"city": {"type": "string"}},
                    },
                },
            }
        },
    }
    data_nested = {"user": {"name": "Alice", "address": {"city": "NYC"}}}
    result = sv.validate(data_nested, schema_nested)
    desc = "1t. Nested object validation passes"
    if not result.valid:
        failures += 1
        print(f"  FAIL: {desc}: {result.errors}")
    else:
        print(f"  PASS: {desc}")

    data_nested_bad = {"user": {"name": "Alice", "address": {"city": 123}}}
    result = sv.validate(data_nested_bad, schema_nested)
    desc = "1u. Nested object type mismatch detected"
    if result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    # ═════════════════════════════════════════════════════════
    # 2. FrameworkConstraintInjector
    # ═════════════════════════════════════════════════════════

    fci = FrameworkConstraintInjector()

    # Register some protocol constraints
    fci.register_protocol_constraints("CP-020", [
        FrameworkConstraint("CP-020", "field", "activity_name: the name of the BPMN activity", "output_schema"),
        FrameworkConstraint("CP-020", "field", "participant: who performs the activity", "output_schema"),
        FrameworkConstraint("CP-020", "field", "input: data or objects entering the activity", "output_schema"),
        FrameworkConstraint("CP-020", "field", "output: data or objects leaving the activity", "output_schema"),
        FrameworkConstraint("CP-020", "required_step", "Ensure activity name is a verb-noun pair", "system_prompt"),
        FrameworkConstraint("CP-020", "value_range", "Check participant is not empty", "post_check"),
    ])

    desc = "2a. Injection bundle for registered protocol"
    bundle = fci.get_injection_bundle("CP-020")
    if len(bundle.system_prompt_additions) != 1 or len(bundle.output_schema_requirements) != 4 or len(bundle.post_check_rules) != 1:
        failures += 1
        print(f"  FAIL: {desc} — sp={len(bundle.system_prompt_additions)}, os={len(bundle.output_schema_requirements)}, pc={len(bundle.post_check_rules)}")
    else:
        print(f"  PASS: {desc}")

    desc = "2b. Injection bundle for unregistered protocol is empty"
    bundle = fci.get_injection_bundle("CP-999")
    if bundle.system_prompt_additions or bundle.output_schema_requirements or bundle.post_check_rules:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "2c. generate_output_schema creates valid schema"
    schema = fci.generate_output_schema("CP-020")
    if schema.get("type") != "object" or len(schema.get("required", [])) != 4:
        failures += 1
        print(f"  FAIL: {desc} — {schema}")
    else:
        print(f"  PASS: {desc}")

    desc = "2d. Generated schema validates correct data"
    test_data = {
        "activity_name": "Approve Loan",
        "participant": "Loan Officer",
        "input": "Loan Application",
        "output": "Approval Decision",
    }
    result = sv.validate(test_data, schema)
    if not result.valid:
        failures += 1
        print(f"  FAIL: {desc}: {result.errors}")
    else:
        print(f"  PASS: {desc}")

    desc = "2e. Generated schema rejects missing field"
    bad_data = {"activity_name": "Approve Loan"}
    result = sv.validate(bad_data, schema)
    if result.valid:
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    # ═════════════════════════════════════════════════════════
    # 3. DeviceNeutralizer
    # ═════════════════════════════════════════════════════════

    dn = DeviceNeutralizer(workspace_root="D:/Phoenix/cursor-knowledge")

    desc = "3a. neutralize_path replaces workspace root"
    result = dn.neutralize_path("D:/Phoenix/cursor-knowledge/foo.md")
    if result != "~/workspace/foo.md":
        failures += 1
        print(f"  FAIL: {desc}: got '{result}'")
    else:
        print(f"  PASS: {desc}")

    desc = "3b. neutralize_path handles nested paths"
    result = dn.neutralize_path("D:\\Phoenix\\cursor-knowledge\\Knowledge-Brain\\protocols\\CP-020.md")
    if result != "~/workspace/Knowledge-Brain/protocols/CP-020.md":
        failures += 1
        print(f"  FAIL: {desc}: got '{result}'")
    else:
        print(f"  PASS: {desc}")

    desc = "3c. neutralize_path scrubs C:\\Users path"
    result = dn.neutralize_path("C:\\Users\\alice\\Projects\\bar")
    if "Users/" not in result or "alice" in result:
        if "alice" in result:  # should be replaced with <user>
            failures += 1
            print(f"  FAIL: {desc}: still has 'alice' → '{result}'")
        else:
            print(f"  PASS: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "3d. restore_path converts ~/workspace back to device path"
    result = dn.restore_path("~/workspace/foo.md")
    if "foo.md" not in result:
        failures += 1
        print(f"  FAIL: {desc}: got '{result}'")
    else:
        print(f"  PASS: {desc}")

    desc = "3e. neutralize_device_info returns cross-platform info"
    info = dn.neutralize_device_info()
    if info.get("os") != "cross-platform" or info.get("workspace") != "~/workspace":
        failures += 1
        print(f"  FAIL: {desc}: {info}")
    else:
        print(f"  PASS: {desc}")

    desc = "3f. get_current_fingerprint returns real device info"
    fp = dn.get_current_fingerprint()
    if not fp.get("hostname") or not fp.get("os"):
        failures += 1
        print(f"  FAIL: {desc}")
    else:
        print(f"  PASS: {desc}")

    desc = "3g. scrub_fingerprint_from_text removes hostname"
    fp = dn.get_current_fingerprint()
    hostname = fp.get("hostname", "")
    if hostname:
        test_text = f"Running on {hostname} at {dn.workspace_root}"
        scrubbed = dn.scrub_fingerprint_from_text(test_text)
        if hostname in scrubbed:
            failures += 1
            print(f"  FAIL: {desc}: hostname still present in '{scrubbed}'")
        else:
            print(f"  PASS: {desc}")
    else:
        print(f"  SKIP: {desc} — no hostname to test")

    # ═════════════════════════════════════════════════════════
    # 4. ToolSelector
    # ═════════════════════════════════════════════════════════

    ts = ToolSelector()

    desc = "4a. data_analysis selects canvas renderer"
    result = ts.select("data_analysis")
    if result.blocked or result.selected_renderer is None or result.selected_renderer.renderer_type != "canvas":
        failures += 1
        print(f"  FAIL: {desc}: blocked={result.blocked}, selected={result.selected_renderer}")
    else:
        print(f"  PASS: {desc} — selected {result.selected_renderer.name}")

    desc = "4b. code_generation selects file renderer"
    result = ts.select("code_generation")
    if result.blocked or result.selected_renderer is None or result.selected_renderer.renderer_type != "file":
        failures += 1
        print(f"  FAIL: {desc}: blocked={result.blocked}, selected={result.selected_renderer}")
    else:
        print(f"  PASS: {desc} — selected {result.selected_renderer.name}")

    desc = "4c. kb_search selects text renderer"
    result = ts.select("kb_search")
    if result.blocked or result.selected_renderer is None or result.selected_renderer.renderer_type != "text":
        failures += 1
        print(f"  FAIL: {desc}: blocked={result.blocked}, selected={result.selected_renderer}")
    else:
        print(f"  PASS: {desc} — selected {result.selected_renderer.name}")

    desc = "4d. notion_crud selects notion renderer"
    result = ts.select("notion_crud")
    if result.blocked or result.selected_renderer is None or result.selected_renderer.renderer_type != "notion":
        failures += 1
        print(f"  FAIL: {desc}: blocked={result.blocked}, selected={result.selected_renderer}")
    else:
        print(f"  PASS: {desc} — selected {result.selected_renderer.name}")

    desc = "4e. generic task selects text renderer"
    result = ts.select("generic")
    if result.blocked or result.selected_renderer is None or result.selected_renderer.renderer_type != "text":
        failures += 1
        print(f"  FAIL: {desc}: blocked={result.blocked}, selected={result.selected_renderer}")
    else:
        print(f"  PASS: {desc} — selected {result.selected_renderer.name}")

    desc = "4f. Unknown task type falls back to generic (text)"
    result = ts.select("nonexistent_task")
    if result.blocked:
        failures += 1
        print(f"  FAIL: {desc}: blocked")
    else:
        print(f"  PASS: {desc} — selected {result.selected_renderer.name if result.selected_renderer else 'none'}")

    desc = "4g. Canvas blocked when all canvas renderers disabled"
    # Disable all canvas renderers
    for r in ts.renderer_map.get("canvas", []):
        r.enabled = False
    result = ts.select("data_analysis")
    if not result.blocked:
        failures += 1
        print(f"  FAIL: {desc}: should be blocked")
    else:
        print(f"  PASS: {desc} — reason: {result.block_reason[:50]}...")
    # Re-enable for subsequent tests
    for r in ts.renderer_map.get("canvas", []):
        r.enabled = True

    desc = "4h. disable_renderer works"
    ok = ts.disable_renderer("markdown_output")
    result = ts.select("kb_search")
    # markdown_output was disabled, but plain_text is still available
    if not ok:
        failures += 1
        print(f"  FAIL: {desc}: disable returned False")
    elif result.blocked:
        failures += 1
        print(f"  FAIL: {desc}: text is blocked after disabling markdown_output")
    else:
        print(f"  PASS: {desc} — remaining renderer: {result.selected_renderer.name}")
    ts.enable_renderer("markdown_output")

    desc = "4i. enable_renderer works"
    ts.disable_renderer("markdown_output")
    ok = ts.enable_renderer("markdown_output")
    result = ts.select("kb_search")
    if not ok:
        failures += 1
        print(f"  FAIL: {desc}: enable returned False")
    elif result.blocked:
        failures += 1
        print(f"  FAIL: {desc}: text is blocked after re-enabling")
    else:
        print(f"  PASS: {desc}")

    desc = "4j. register_renderer adds new renderer"
    ts.register_renderer("custom", Renderer("custom_output", "custom", True, "Custom renderer"))
    result = ts.select_for_medium("custom")
    if not result:
        failures += 1
        print(f"  FAIL: {desc}: custom renderer not found")
    else:
        print(f"  PASS: {desc}")

    desc = "4k. Degradation path suggested for blocked canvas"
    path = ts._suggest_degradation("canvas")
    if "text" not in path:
        failures += 1
        print(f"  FAIL: {desc}: {path}")
    else:
        print(f"  PASS: {desc}")

    # ── 4l–4q. chart_diagram + reliability tests ──────────────

    desc = "4l. chart_diagram selects svg renderer (verified)"
    result = ts.select("chart_diagram")
    if result.blocked:
        failures += 1
        print(f"  FAIL: {desc}: blocked — {result.block_reason[:60]}...")
    elif result.selected_renderer is None or result.selected_renderer.renderer_type != "svg":
        failures += 1
        print(f"  FAIL: {desc}: selected={result.selected_renderer}")
    else:
        print(f"  PASS: {desc} — selected {result.selected_renderer.name}, reliability={result.selected_reliability}")

    desc = "4m. chart_diagram selected renderer is verified"
    result = ts.select("chart_diagram")
    if result.selected_reliability != "verified":
        failures += 1
        print(f"  FAIL: {desc}: reliability={result.selected_reliability}")
    else:
        print(f"  PASS: {desc}")

    desc = "4n. check_reliability returns correct status"
    if ts.check_reliability("svg_edge_print") != "verified":
        failures += 1
        print(f"  FAIL: {desc}: svg_edge_print")
    elif ts.check_reliability("svg_cairosvg") != "unreliable":
        failures += 1
        print(f"  FAIL: {desc}: svg_cairosvg")
    elif ts.check_reliability("react_canvas") != "degraded":
        failures += 1
        print(f"  FAIL: {desc}: react_canvas")
    elif ts.check_reliability("nonexistent") != "unknown":
        failures += 1
        print(f"  FAIL: {desc}: nonexistent")
    else:
        print(f"  PASS: {desc}")

    desc = "4o. chart_diagram blocked when all svg renderers disabled"
    for r in ts.renderer_map.get("svg", []):
        r.enabled = False
    result = ts.select("chart_diagram")
    if not result.blocked:
        failures += 1
        print(f"  FAIL: {desc}: should be blocked")
    else:
        print(f"  PASS: {desc} — reason: {result.block_reason[:60]}...")
    # Re-enable
    for r in ts.renderer_map.get("svg", []):
        r.enabled = True

    desc = "4p. chart_diagram blocked when all svg renderers are unreliable"
    # Disable all verified renderers, enable only unreliable ones
    for r in ts.renderer_map.get("svg", []):
        r.enabled = (r.name == "svg_cairosvg")
    result = ts.select("chart_diagram")
    if not result.blocked:
        failures += 1
        print(f"  FAIL: {desc}: should be blocked (only cairosvg enabled, marked unreliable)")
    else:
        print(f"  PASS: {desc} — degradation: {result.degradation_path[:60]}...")
    # Re-enable verified renderers
    for r in ts.renderer_map.get("svg", []):
        r.enabled = True

    desc = "4q. RenderEngineCapability has recommended_renderer"
    from p008.tool_selector import (
        TASK_CAPABILITY_MAP,
        RenderEngineCapability,
    )
    caps = TASK_CAPABILITY_MAP.get("chart_diagram", [])
    engine_caps = [c for c in caps if isinstance(c, RenderEngineCapability)]
    if not engine_caps:
        failures += 1
        print(f"  FAIL: {desc}: no RenderEngineCapability found for chart_diagram")
    elif engine_caps[0].recommended_renderer != "svg_edge_print":
        failures += 1
        print(f"  FAIL: {desc}: recommended_renderer={engine_caps[0].recommended_renderer}")
    else:
        print(f"  PASS: {desc} — found {len(engine_caps)} RenderEngineCapability(ies)")

    # ── Summary ──
    print(f"\n{'='*50}")
    if failures == 0:
        print("  All constraint engine tests PASSED")
    else:
        print(f"  {failures} test(s) FAILED")
    return failures


if __name__ == "__main__":
    sys.exit(run_tests())
