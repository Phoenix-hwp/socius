"""Constraint Engine — schema validation and framework constraint injection.

Part of Guard MVP v0.2. Two sub-engines:

1. SchemaValidator — validates LLM JSON output against a JSON Schema.
   Used by LLM#1, LLM#2, LLM#3 output gates.

2. FrameworkConstraintInjector — converts KB protocol steps into constraint
   instructions that get injected into LLM prompts as output limits.

Both operate statelessly and can be called independently from Guard's pipeline.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional


# ── SchemaValidator ────────────────────────────────────────────────

@dataclass
class SchemaValidationResult:
    """Result of a schema validation."""

    valid: bool
    errors: list[dict[str, Any]] = field(default_factory=list)
    schema_id: str = ""
    validated_fields: list[str] = field(default_factory=list)

    def describe(self) -> str:
        if self.valid:
            return f"Schema validation PASSED ({self.schema_id}) — {len(self.validated_fields)} fields checked"
        err_msgs = [e.get("message", str(e)) for e in self.errors]
        return f"Schema validation FAILED ({self.schema_id}) — {len(self.errors)} error(s): {'; '.join(err_msgs[:3])}"


class SchemaValidator:
    """Validates JSON data against JSON Schema definitions.

    Uses a lightweight inline implementation rather than importing jsonschema
    to avoid external dependency at Guard MVP stage. For production, replace
    with jsonschema.validate().
    """

    JSON_TYPES = {"string", "number", "integer", "boolean", "object", "array", "null"}

    def __init__(self, schema: Optional[dict[str, Any]] = None) -> None:
        self.schema = schema or {}

    def validate(self, data: Any, schema: Optional[dict[str, Any]] = None) -> SchemaValidationResult:
        """Validate data against the given (or stored) schema.

        Args:
            data: JSON-serializable data to validate.
            schema: JSON Schema dict. If None, uses self.schema.

        Returns:
            SchemaValidationResult with valid flag and error list.
        """
        schema = schema or self.schema
        schema_id = schema.get("$id", schema.get("title", "unnamed"))
        result = SchemaValidationResult(valid=True, schema_id=schema_id)

        self._validate_node(data, schema, "/", result)
        return result

    def validate_json_string(self, json_str: str, schema: Optional[dict[str, Any]] = None) -> SchemaValidationResult:
        """Parse JSON string and validate against schema.

        Returns failed result if JSON is malformed.
        """
        schema = schema or self.schema
        schema_id = schema.get("$id", schema.get("title", "unnamed"))
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            return SchemaValidationResult(
                valid=False,
                errors=[{"path": "/", "message": f"Invalid JSON: {e}"}],
                schema_id=schema_id,
            )
        return self.validate(data, schema)

    # ── Internal validation logic ─────────────────────────────

    def _validate_node(
        self,
        data: Any,
        schema: dict,
        path: str,
        result: SchemaValidationResult,
    ) -> None:
        """Recursive schema validation."""
        if not isinstance(schema, dict):
            return

        s_type = schema.get("type")
        if s_type:
            self._check_type(data, s_type, path, result)

        # Object validation
        if s_type == "object" and isinstance(data, dict):
            self._validate_object(data, schema, path, result)

        # Array validation
        if s_type == "array" and isinstance(data, list):
            self._validate_array(data, schema, path, result)

        # Enum
        if "enum" in schema:
            if data not in schema["enum"]:
                result.valid = False
                result.errors.append({
                    "path": path,
                    "message": f"Value {data!r} not in enum {schema['enum']}",
                })

        # Const
        if "const" in schema:
            if data != schema["const"]:
                result.valid = False
                result.errors.append({
                    "path": path,
                    "message": f"Expected const {schema['const']!r}, got {data!r}",
                })

        # String constraints
        if s_type == "string" and isinstance(data, str) and "pattern" in schema:
            import re
            if not re.match(schema["pattern"], data):
                result.valid = False
                result.errors.append({
                    "path": path,
                    "message": f"String {data!r} does not match pattern {schema['pattern']}",
                })

        if s_type == "string" and isinstance(data, str):
            if "minLength" in schema and len(data) < schema["minLength"]:
                result.valid = False
                result.errors.append({
                    "path": path,
                    "message": f"String length {len(data)} < minLength {schema['minLength']}",
                })
            if "maxLength" in schema and len(data) > schema["maxLength"]:
                result.valid = False
                result.errors.append({
                    "path": path,
                    "message": f"String length {len(data)} > maxLength {schema['maxLength']}",
                })

        # Numeric constraints
        if s_type in ("number", "integer") and isinstance(data, (int, float)):
            if "minimum" in schema and data < schema["minimum"]:
                result.valid = False
                result.errors.append({
                    "path": path,
                    "message": f"Value {data} < minimum {schema['minimum']}",
                })
            if "maximum" in schema and data > schema["maximum"]:
                result.valid = False
                result.errors.append({
                    "path": path,
                    "message": f"Value {data} > maximum {schema['maximum']}",
                })

    def _check_type(
        self,
        data: Any,
        expected: str | list[str],
        path: str,
        result: SchemaValidationResult,
    ) -> None:
        """Check that data matches the expected type(s)."""
        python_type = type(data).__name__

        type_map = {
            "string": "str",
            "number": ("float", "int"),
            "integer": "int",
            "boolean": "bool",
            "object": "dict",
            "array": "list",
            "null": "NoneType",
        }

        if isinstance(expected, list):
            type_names = expected
        else:
            type_names = [expected]

        valid = False
        for tn in type_names:
            mapped = type_map.get(tn, tn)
            if isinstance(mapped, tuple):
                if python_type in mapped:
                    valid = True
                    break
            elif python_type == mapped:
                valid = True
                break

        if not valid:
            result.valid = False
            result.errors.append({
                "path": path,
                "message": f"Expected type(s) {type_names}, got {python_type}",
            })

    def _validate_object(
        self,
        data: dict,
        schema: dict,
        path: str,
        result: SchemaValidationResult,
    ) -> None:
        """Validate object properties and required fields."""
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        for field_name in required:
            field_path = f"{path}/{field_name}"
            if field_name not in data:
                result.valid = False
                result.errors.append({
                    "path": field_path,
                    "message": f"Required field '{field_name}' missing",
                })
            else:
                result.validated_fields.append(field_path)

        for field_name, field_schema in properties.items():
            if field_name in data:
                field_path = f"{path}/{field_name}"
                self._validate_node(data[field_name], field_schema, field_path, result)
                if result.valid and field_path not in result.validated_fields:
                    result.validated_fields.append(field_path)

        # additionalProperties: false
        if schema.get("additionalProperties") is False:
            allowed = set(properties.keys())
            for key in data:
                if key not in allowed:
                    result.valid = False
                    result.errors.append({
                        "path": f"{path}/{key}",
                        "message": f"Additional property '{key}' not allowed",
                    })

    def _validate_array(
        self,
        data: list,
        schema: dict,
        path: str,
        result: SchemaValidationResult,
    ) -> None:
        """Validate array items."""
        items_schema = schema.get("items")
        if items_schema is None:
            return

        for i, item in enumerate(data):
            item_path = f"{path}/{i}"
            self._validate_node(item, items_schema, item_path, result)


# ── FrameworkConstraintInjector ────────────────────────────────────

@dataclass
class FrameworkConstraint:
    """A single constraint derived from a KB protocol step."""

    constraint_id: str          # e.g. "CP-020"
    constraint_type: str        # "format" | "field" | "value_range" | "required_step"
    rule: str                   # human-readable constraint rule
    inject_as: str              # "system_prompt" | "output_schema" | "post_check"


@dataclass
class InjectionBundle:
    """Complete set of constraints to inject into an LLM call."""

    protocol_id: str
    system_prompt_additions: list[str] = field(default_factory=list)
    output_schema_requirements: list[dict[str, Any]] = field(default_factory=list)
    post_check_rules: list[str] = field(default_factory=list)


class FrameworkConstraintInjector:
    """Converts KB protocol steps into injectable constraints.

    For each protocol in the KB, extracts its step structure and converts
    each step into a constraint that the LLM must follow when generating
    output conforming to that protocol.

    Example:
        Protocol "CP-020 BPMN活动定义" has steps:
            1. 定义活动名称
            2. 标注参与者
            3. 标注输入输出

        → Generates output_schema with required fields:
            activity_name, participant, input, output

    Guard MVP v0.2 scope: manual registration of known protocols.
    Later (v0.3+) auto-extraction from protocol Markdown.
    """

    def __init__(self) -> None:
        self._constraints: dict[str, list[FrameworkConstraint]] = {}

    def register_protocol_constraints(
        self, protocol_id: str, constraints: list[FrameworkConstraint]
    ) -> None:
        """Register constraints for a KB protocol."""
        self._constraints[protocol_id] = constraints

    def get_injection_bundle(self, protocol_id: str) -> InjectionBundle:
        """Build an InjectionBundle for a given protocol.

        If no constraints are registered for this protocol, returns an empty bundle.
        """
        constraints = self._constraints.get(protocol_id, [])
        bundle = InjectionBundle(protocol_id=protocol_id)

        for c in constraints:
            if c.inject_as == "system_prompt":
                bundle.system_prompt_additions.append(c.rule)
            elif c.inject_as == "output_schema":
                bundle.output_schema_requirements.append({
                    "constraint_id": c.constraint_id,
                    "type": c.constraint_type,
                    "rule": c.rule,
                })
            elif c.inject_as == "post_check":
                bundle.post_check_rules.append(c.rule)

        return bundle

    def generate_output_schema(self, protocol_id: str) -> dict[str, Any]:
        """Generate a JSON Schema fragment from registered constraints.

        Combines output_schema_requirements into a valid schema dict.
        """
        bundle = self.get_injection_bundle(protocol_id)
        required = []
        properties = {}

        for req in bundle.output_schema_requirements:
            field_name = req["rule"].split(":")[0].strip() if ":" in req["rule"] else req["rule"]
            required.append(field_name)
            properties[field_name] = {
                "type": "string",
                "description": req["rule"],
            }

        return {
            "type": "object",
            "required": required,
            "properties": properties,
            "additionalProperties": False,
        }

    # ── Workflow step integrity injection (Batch 2026-05-21) ────────

    def inject_workflow_steps(
        self,
        workflow_results: list,
    ) -> str:
        """Format missing workflow steps as a system prompt addition.

        Uses WorkflowStepTracker.format_constraint_injection() format.
        This is a passthrough — the actual formatting is done by the tracker.
        """
        from .state_persistence import WorkflowStepTracker

        # Reconstruct a tracker just for formatting
        tracker = WorkflowStepTracker(definitions_path="")
        return tracker.format_constraint_injection(workflow_results)
