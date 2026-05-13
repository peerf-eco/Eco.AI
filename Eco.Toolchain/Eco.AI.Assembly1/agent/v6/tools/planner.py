"""PLANNER tools — read_component, list_components, submit_plan."""
from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel, Field
from agent.v6.eco_agent import EcoTool, ToolResult
from agent.v6.tools.sdk_layout import resolve_component_root, list_component_roots


class ReadComponentArgs(BaseModel):
    name: str = Field(..., description="Component name without _DK_v.* suffix (e.g. 'Eco.Math.C89')")


class ListComponentsArgs(BaseModel):
    pass


class SubmitPlanArgs(BaseModel):
    project_name: str = Field(..., description="Short project identifier (no spaces)")
    plan_md: str = Field(..., description="Full plan in Markdown, MUST include '## Acceptance criteria' section")
    components: list[dict] = Field(..., description="List of {cid, version, name, reason}")
    acceptance_criteria: list[str] = Field(..., description="Explicit pass/fail rules for tester")


def _read_component(args: ReadComponentArgs, sdk_root: Path) -> ToolResult:
    root = resolve_component_root(sdk_root, args.name)
    if root is None:
        return ToolResult(
            content=f"Component '{args.name}' not found in {sdk_root}",
            is_error=True,
        )
    shared = root / "SharedFiles"
    if not shared.exists():
        return ToolResult(
            content=f"{root.name}: no SharedFiles/ subdir under resolved root {root}",
            is_error=True,
        )
    parts = []
    for f in sorted(shared.rglob("*.h")):
        parts.append(f"=== {f.relative_to(root)} ===\n{f.read_text(errors='replace')}")
    if not parts:
        return ToolResult(
            content=f"{root.name}: no .h files in SharedFiles/",
            is_error=True,
        )
    return ToolResult(
        content="\n\n".join(parts),
        details={"package": root.name, "resolved_root": str(root)},
    )


def _list_components(_args: ListComponentsArgs, sdk_root: Path) -> ToolResult:
    names = list_component_roots(sdk_root)
    return ToolResult(content="\n".join(names))


def make_planner_tools(sdk_root: Path) -> list[EcoTool]:
    return [
        EcoTool(
            name="read_component",
            description="Read the SharedFiles/*.h of an EcoOS SDK component package.",
            args_schema=ReadComponentArgs,
            execute=lambda a: _read_component(a, sdk_root),
        ),
        EcoTool(
            name="list_components",
            description="List available EcoOS SDK component packages by base name.",
            args_schema=ListComponentsArgs,
            execute=lambda a: _list_components(a, sdk_root),
        ),
        EcoTool(
            name="submit_plan",
            description="Submit the final plan. The agent stops after this.",
            args_schema=SubmitPlanArgs,
            execute=lambda _a: ToolResult(content="(stop tool — never executed)"),
        ),
    ]
