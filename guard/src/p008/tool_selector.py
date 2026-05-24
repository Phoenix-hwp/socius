"""Tool Selector — task→capability→output_medium→renderer ternary mapping.

Guard MVP v0.3. Three-layer mapping + rendering pipeline reliability check:

    TASK_TYPE → REQUIRED_CAPABILITIES → OUTPUT_MEDIUM → RENDERER
                                                    ↓
                                            RENDERER_RELIABILITY check
                                            (verified / degraded / unreliable / unknown)

Design principle:
    LLM is competent at content generation (SVG design, Mermaid DSL, layout logic).
    LLM is fragile at the rendering pipeline (encoding, font loading, PDF conversion).
    The ToolSelector separates these two concerns: content capabilities declare what
    the LLM can generate; RENDERER_RELIABILITY declares whether the local rendering
    pipeline can reliably convert that content into the final deliverable.

When a renderer is marked 'unreliable', the selector blocks execution and suggests
either a verified alternative or a degradation path.

Data sources (registry files):
    - Skills_Library/task-type-registry.md      (task_type → capabilities)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ── Data structures ───────────────────────────────────────────────

@dataclass
class TaskCapability:
    """A single capability required by a task type."""
    capability: str
    description: str = ""
    mandatory: bool = True


@dataclass
class RenderEngineCapability:
    """Capability that requires an external rendering pipeline (not LLM-generated text).

    These capabilities mark the boundary where content generation (LLM) ends
    and rendering pipeline (external renderer) begins. Examples:
      - svg_render: LLM can design the SVG, but encoding + font + PDF conversion
        requires a browser-based renderer or a verified external skill.
      - mermaid_render: LLM can write valid Mermaid DSL, but rendering to SVG/PNG
        requires a Mermaid CLI with Puppeteer.
      - canvas_render: LLM can structure data, but interactive viz needs React Canvas.
    """
    capability: str
    description: str = ""
    recommended_renderer: str = ""  # Name of the verified renderer for this capability


@dataclass
class OutputMedium:
    """What the output medium is for a task type."""
    medium: str          # "text" | "canvas" | "shell" | "file" | "notion" | "audio" | "svg" | "mermaid"
    description: str = ""


@dataclass
class Renderer:
    """A renderer available in the tool pool."""
    name: str
    renderer_type: str   # matches OutputMedium.medium
    enabled: bool = True
    description: str = ""
    reliability: str = "unknown"  # verified | degraded | unreliable | unknown


@dataclass
class ToolSelectionResult:
    """Result of a tool selection query."""

    task_type: str
    capabilities: list[TaskCapability]
    output_medium: str
    matching_renderers: list[Renderer]
    selected_renderer: Optional[Renderer] = None
    blocked: bool = False
    block_reason: str = ""
    degradation_path: str = ""
    selected_reliability: str = "unknown"  # reliability of the selected renderer


# ── Ternary mapping tables ────────────────────────────────────────

# Layer 1: task_type → list of required capabilities
TASK_CAPABILITY_MAP: dict[str, list[TaskCapability]] = {
    "data_analysis": [
        TaskCapability("data_query", "Ability to query structured data sources"),
        TaskCapability("chart_render", "Ability to render charts and tables", mandatory=True),
    ],
    "code_generation": [
        TaskCapability("file_write", "Ability to write files to disk"),
        TaskCapability("linter", "Ability to lint generated code"),
    ],
    "notion_crud": [
        TaskCapability("notion_api", "Access to Notion API"),
        TaskCapability("markdown_render", "Markdown to Notion blocks conversion"),
    ],
    "kb_search": [
        TaskCapability("semantic_search", "Semantic search over knowledge base"),
        TaskCapability("text_render", "Plain text or Markdown output"),
    ],
    "simulation": [
        TaskCapability("sandbox", "Isolated execution environment"),
        TaskCapability("logging", "Structured logging and metrics"),
        TaskCapability("text_render", "Simulation report rendering"),
    ],
    "system_audit": [
        TaskCapability("file_scan", "Recursive file system scanning"),
        TaskCapability("json_parse", "JSON/JSONL parsing and validation"),
        TaskCapability("text_render", "Structured report output"),
    ],
    "skill_execution": [
        TaskCapability("subprocess", "Subprocess execution (isolated)"),
        TaskCapability("file_write", "File write with path restriction"),
        TaskCapability("text_render", "Execution logs and results"),
    ],
    "conversation_management": [
        TaskCapability("text_render", "Text-based dialogue output"),
    ],
    "knowledge_digestion": [
        TaskCapability("md_parse", "Markdown parsing and structure extraction"),
        TaskCapability("file_write", "Protocol file generation"),
    ],
    "chart_diagram": [
        TaskCapability("svg_generate", "Ability to generate SVG structural content (LLM)", mandatory=True),
        TaskCapability("mermaid_generate", "Ability to generate Mermaid DSL (LLM)", mandatory=False),
        RenderEngineCapability("svg_render", "Reliable SVG→PDF/PNG rendering (external pipeline required)", "svg_edge_print"),
        RenderEngineCapability("mermaid_render", "Mermaid DSL→SVG/PNG rendering (Mermaid CLI required)", "mermaid_cli"),
    ],
    "generic": [
        TaskCapability("text_render", "Generic text output"),
    ],
}


# Layer 2: output_medium → list of compatible renderer types
# (The medium is what the OUTPUT needs to be. It's the user-visible deliverable.)
OUTPUT_MEDIUM_MAP: dict[str, OutputMedium] = {
    "data_analysis": OutputMedium("canvas", "Interactive charts and tables"),
    "code_generation": OutputMedium("file", "Source code files written to disk"),
    "notion_crud": OutputMedium("notion", "Notion page or database row"),
    "kb_search": OutputMedium("text", "Markdown search results with citations"),
    "simulation": OutputMedium("text", "Formatted simulation report (text)"),
    "system_audit": OutputMedium("text", "Structured audit report (text)"),
    "skill_execution": OutputMedium("text", "Execution log and diff summary (text)"),
    "conversation_management": OutputMedium("text", "Conversational text output"),
    "knowledge_digestion": OutputMedium("file", "Protocol markdown files"),
    "chart_diagram": OutputMedium("svg", "Vector graphics (SVG) — requires rendering pipeline"),
    "generic": OutputMedium("text", "Generic text output"),
}


# Layer 3: renderer_type → list of renderers available in the tool pool
# (Register renderers that exist in the current execution environment)
FORMAT_RENDERER_MAP: dict[str, list[Renderer]] = {
    "text": [
        Renderer("markdown_output", "text", True, "Standard Markdown rendering in chat", "verified"),
        Renderer("plain_text", "text", True, "Plain text output", "verified"),
    ],
    "canvas": [
        Renderer("react_canvas", "canvas", True, "Interactive React canvas component", "degraded"),
    ],
    "notion": [
        Renderer("notion_mcp", "notion", True, "Notion MCP API tool", "verified"),
    ],
    "file": [
        Renderer("file_write", "file", True, "File write tool", "verified"),
    ],
    "shell": [
        Renderer("subprocess", "shell", True, "Shell execution tool", "degraded"),
    ],
    "audio": [
        Renderer("tts_speak", "audio", True, "Text-to-speech output", "degraded"),
    ],
    "svg": [
        Renderer("svg_edge_print", "svg", True,
                 "Edge headless print SVG→PDF (Windows verified 2026-05-20)", "verified"),
        Renderer("svg_browser_print", "svg", False,
                 "Generic browser print (disabled; prefer svg_edge_print on Windows)", "verified"),
        Renderer("svg_cairosvg", "svg", False,
                 "cairosvg Python library (disabled; requires cairo-2.dll unavailable on Windows)", "unreliable"),
    ],
    "mermaid": [
        Renderer("mermaid_cli", "mermaid", True,
                 "Mermaid CLI with Puppeteer (Chromium-based, reliable rendering)", "verified"),
    ],
}


# ── Rendering Pipeline Reliability ─────────────────────────────────
#
# RENDERER_RELIABILITY declares whether a renderer's local rendering pipeline
# can reliably convert LLM-generated content into the final deliverable.
#
# This table separates LLM competence (content generation) from pipeline
# reliability (encoding, font loading, format conversion).
#
# Status meanings:
#   verified   — Tested on this platform; known to produce correct output.
#   degraded   — Functional but with known quality risks (e.g. formatting drift).
#   unreliable — Known to fail on this platform (e.g. missing system libraries).
#   unknown    — Not yet tested on this platform.
#
# When all enabled renderers for a required medium are 'unreliable',
# the selector blocks execution and suggests a degradation path or
# an external skill (registered in Task-Type-Registry.json).

RENDERER_RELIABILITY: dict[str, str] = {
    # Text renderers — LLM-native, no external pipeline needed
    "markdown_output": "verified",
    "plain_text": "verified",
    # Canvas — React rendering, known formatting drift issues
    "react_canvas": "degraded",
    # Notion — MCP API, tested stable
    "notion_mcp": "verified",
    # File write — OS-native, no rendering step
    "file_write": "verified",
    # Shell — environment-dependent, fragmentation risk
    "subprocess": "degraded",
    # Audio — TTS engine, platform-dependent
    "tts_speak": "degraded",
    # SVG renderers — pipeline-heavy
    "svg_edge_print": "verified",      # Confirmed working 2026-05-20
    "svg_browser_print": "verified",   # Chromium-based, equivalent to Edge
    "svg_cairosvg": "unreliable",      # Missing cairo-2.dll on Windows
    # Mermaid — Puppeteer (Chromium), reliable pipeline
    "mermaid_cli": "verified",
}


# ── Tool Selector ─────────────────────────────────────────────────

class ToolSelector:
    """Select the right renderer for a task type via ternary mapping + reliability check.

    TASK_TYPE → OUTPUT_MEDIUM → RENDERER_TYPE → RENDERER
                                                    ↓
                                            RENDERER_RELIABILITY check
                                            (verified / degraded / unreliable / unknown)

    If the selected renderer is 'unreliable', execution is blocked and
    a degradation path or external skill is suggested.

    Design rationale:
        LLM is competent at content generation (SVG design, Mermaid DSL, layout).
        LLM is fragile at the rendering pipeline (encoding, fonts, PDF conversion).
        This selector separates these two concerns: content capabilities declare
        what LLM can generate; RENDERER_RELIABILITY declares whether the local
        pipeline can convert that content into the final deliverable.

    Usage:
        selector = ToolSelector()
        result = selector.select("chart_diagram")
        if result.blocked:
            print(f"Blocked: {result.block_reason}")
            print(f"Degrade: {result.degradation_path}")
        else:
            print(f"Using renderer: {result.selected_renderer.name}")
            print(f"Reliability: {result.selected_reliability}")
    """

    def __init__(
        self,
        capability_map: Optional[dict] = None,
        output_medium_map: Optional[dict] = None,
        renderer_map: Optional[dict] = None,
    ) -> None:
        self.capability_map = capability_map or TASK_CAPABILITY_MAP
        self.output_medium_map = output_medium_map or OUTPUT_MEDIUM_MAP
        self.renderer_map = renderer_map or FORMAT_RENDERER_MAP

    # ── Public API ────────────────────────────────────────────

    def select(self, task_type: str) -> ToolSelectionResult:
        """Select the appropriate renderer for a given task type.

        Returns ToolSelectionResult with selected_renderer if found and reliable,
        or blocked=True with reason and degradation path if not.

        Selection logic:
            1. Map task_type → capabilities
            2. Map task_type → output_medium
            3. Filter enabled renderers for that medium
            4. Check reliability of the best enabled renderer
            5. If unreliable → block and suggest verified alternative or external skill
        """
        capabilities = self.capability_map.get(
            task_type, self.capability_map.get("generic", [])
        )

        # Layer 2: task → output medium
        output_medium = self.output_medium_map.get(
            task_type, self.output_medium_map.get("generic")
        )
        medium_str = output_medium.medium if output_medium else "text"

        # Layer 3: output medium → renderers
        renderers = self.renderer_map.get(medium_str, [])
        enabled = [r for r in renderers if r.enabled]

        result = ToolSelectionResult(
            task_type=task_type,
            capabilities=capabilities,
            output_medium=medium_str,
            matching_renderers=enabled,
        )

        if not enabled:
            result.blocked = True
            result.block_reason = (
                f"No enabled renderer for output medium '{medium_str}' "
                f"(task_type={task_type}). Pool has {len(renderers)} renderer(s) "
                f"but all are disabled."
            )
            result.degradation_path = self._suggest_degradation(medium_str)
        else:
            selected = enabled[0]
            reliability = RENDERER_RELIABILITY.get(selected.name, selected.reliability)
            result.selected_renderer = selected
            result.selected_reliability = reliability

            # Block if the selected renderer is unreliable
            if reliability == "unreliable":
                result.blocked = True
                result.block_reason = (
                    f"Selected renderer '{selected.name}' is marked 'unreliable' "
                    f"on this platform. Reason: {selected.description}. "
                    f"All enabled renderers for '{medium_str}': "
                    f"{[r.name + '(' + RENDERER_RELIABILITY.get(r.name, r.reliability) + ')' for r in enabled]}"
                )
                # Try to find a verified alternative
                verified = [r for r in renderers
                            if r.enabled and RENDERER_RELIABILITY.get(r.name, r.reliability) == "verified"]
                if verified:
                    result.degradation_path = (
                        f"Verified alternative available: '{verified[0].name}'. "
                        f"Switch to this renderer or install dependencies for '{selected.name}'."
                    )
                else:
                    result.degradation_path = self._suggest_render_pipeline_degradation(task_type, medium_str)
            else:
                result.blocked = False

        return result

    def select_for_medium(self, output_medium: str) -> list[Renderer]:
        """Get all enabled renderers for a given output medium (e.g. 'canvas')."""
        renderers = self.renderer_map.get(output_medium, [])
        return [r for r in renderers if r.enabled]

    def register_renderer(
        self, renderer_type: str, renderer: Renderer
    ) -> None:
        """Register a new renderer in the pool."""
        if renderer_type not in self.renderer_map:
            self.renderer_map[renderer_type] = []
        self.renderer_map[renderer_type].append(renderer)

    def enable_renderer(self, renderer_name: str) -> bool:
        """Enable a renderer by name. Returns True if found."""
        for renderers in self.renderer_map.values():
            for r in renderers:
                if r.name == renderer_name:
                    r.enabled = True
                    return True
        return False

    def disable_renderer(self, renderer_name: str) -> bool:
        """Disable a renderer by name. Returns True if found."""
        for renderers in self.renderer_map.values():
            for r in renderers:
                if r.name == renderer_name:
                    r.enabled = False
                    return True
        return False

    # ── Helpers ───────────────────────────────────────────────

    def check_reliability(self, renderer_name: str) -> str:
        """Check the reliability of a renderer by name.

        Returns one of: verified | degraded | unreliable | unknown
        """
        return RENDERER_RELIABILITY.get(renderer_name, "unknown")

    @staticmethod
    def _suggest_degradation(medium: str) -> str:
        """Suggest a degradation path when a renderer is unavailable."""
        degradation_map = {
            "canvas": "Degrade to 'text' renderer (markdown tables instead of charts)",
            "notion": "Degrade to 'file' renderer (write Markdown to local file instead of Notion)",
            "file": "Degrade to 'text' renderer (inline output in chat)",
            "shell": "Degrade to 'text' renderer (instruct user to run command manually)",
            "audio": "Degrade to 'text' renderer (output text for user to read)",
            "svg": "Degrade to browser-based print (Edge --headless --print-to-pdf) or use external skill 'skill-pretty-mermaid'",
            "mermaid": "Degrade to raw Mermaid DSL output + manual rendering, or use external skill 'skill-pretty-mermaid'",
            "text": "No fallback — text renderer is the universal base. Check renderer configuration.",
        }
        return degradation_map.get(medium, f"No degradation path for '{medium}'")

    @staticmethod
    def _suggest_render_pipeline_degradation(task_type: str, medium: str) -> str:
        """Suggest degradation when no verified renderer exists for a rendering-pipeline-heavy task.

        This is the third-layer fallback: when all enabled renderers for a medium
        are unreliable, suggest either an external skill (from Task-Type-Registry)
        or a manual workaround.
        """
        skill_suggestions = {
            "chart_diagram": (
                "No verified SVG/Mermaid renderer available. "
                "Suggestions: (1) install Mermaid CLI with Puppeteer, "
                "(2) use Edge headless print (svg_edge_print), "
                "(3) use external skill 'skill-pretty-mermaid' for Mermaid→SVG conversion, "
                "(4) manually render the SVG in a browser and save as PDF."
            ),
        }
        return skill_suggestions.get(
            task_type,
            f"No verified renderer for '{medium}' and no task-specific degradation path.",
        )
