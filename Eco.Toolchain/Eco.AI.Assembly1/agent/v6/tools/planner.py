"""PLANNER tools — search_marketplace, read_component, list_components, submit_plan."""
from __future__ import annotations
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from agent.v6.eco_agent import EcoTool, ToolResult
from agent.v6.tools.sdk_layout import resolve_component_root, list_component_roots
from agent.v6.tools.rag import make_search_marketplace_tool


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
        has_build = (root / "BuildFiles").is_dir()
        hint = " (build-only package: no public headers, only .lib/.a)" if has_build else ""
        return ToolResult(
            content=f"{root.name}: no SharedFiles/ subdir under resolved root {root}{hint}",
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


def make_planner_tools(
    sdk_root: Path,
    *,
    index_path: Optional[Path] = None,
) -> list[EcoTool]:
    """Build the planner's tool set.

    ``search_marketplace`` is included so the planner can discover WHICH
    SDK components implement a capability before drilling into their
    headers. Order of use in the planner prompt: search_marketplace →
    read_component (on the candidate) → submit_plan. See
    ``feedback_prompts_positive_procedure.md`` for why we frame this as
    a positive linear procedure instead of a list of bans.

    Args:
        sdk_root: Local SDK mirror used by read_component / list_components.
        index_path: Path to marketplace_index.sqlite. ``None`` lets
                    ``make_search_marketplace_tool`` resolve from
                    ``MARKETPLACE_INDEX_PATH`` env (production volume at
                    /app/marketplace_index.sqlite) or its default.
    """
    return [
        make_search_marketplace_tool(index_path=index_path),
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
