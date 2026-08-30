"""Role permission enforcement — tool-group filtering + command allowlist.

Permissions are configured per role (roles are the harness's trust boundary;
models are interchangeable providers) with harness-level defaults resolved in
``agent.config.loader``. Enforcement happens here, at agent-assembly time:

1. Tool-group filtering — denied tools are REMOVED from the agent's toolset
   before the system prompt is built, so the model never even sees a tool it
   may not call (no prompt-injection surface, no wasted tokens).
2. Command allowlist — execution tools (``run_build``, ``run_artifact``,
   ``eco_cli``) are wrapped with a token check. Semantics:
     - ``["*"]`` (the default) allows everything;
     - an EMPTY list denies every gated command (explicit deny-all);
     - otherwise each token must appear verbatim in the list.
   Tokens per tool: run_build → the make TARGET, or ``"make"`` for a default
   build; run_artifact → the artifact file BASENAME; eco_cli → the SUBCOMMAND.

This module is a POLICY layer on top of the tools' own sandboxes (project_dir
containment, eco-cli subcommand whitelist), not a replacement for them: the
allowlist narrows which programs/targets may run, while path containment and
argument validation stay with each tool. It does NOT apply to external CLI
backends (pi/codex/claude/grok) — they execute in their own process with
their own tool policy; the settings UI marks those roles accordingly.

Handoff/stop tools (``to_*``, ``fail``) are pipeline plumbing and are never
filtered.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from eco_harness.agent.config.loader import HarnessConfig, PermissionSpec, RoleSpec
from eco_harness.agent.internal.eco_agent import EcoTool, ToolResult

# Permission group → concrete tool names. Keep in sync with the settings UI.
TOOL_GROUPS: dict[str, frozenset[str]] = {
    "fs_read": frozenset({
        "grep", "glob", "read", "read_file", "list_dir", "read_component_profile",
    }),
    "fs_write": frozenset({"write_file"}),
    "build": frozenset({"run_build"}),
    "execute": frozenset({"run_artifact"}),
    "rag_search": frozenset({"search_marketplace"}),
    "skills": frozenset({"read_skill"}),
    "network": frozenset({"eco_cli", "eco_wizard"}),
}

# Tools whose execution token is checked against the ``commands`` allowlist.
_COMMAND_GATED_TOOLS = frozenset({"run_build", "run_artifact", "eco_cli"})


def _denied_tools(perms: PermissionSpec) -> set[str]:
    denied: set[str] = set()
    for group, allowed in perms.model_dump().items():
        if allowed is False and group in TOOL_GROUPS:
            denied |= TOOL_GROUPS[group]
    return denied


def _token_allowed(allowlist: list[str], token: str | None) -> bool:
    """Wildcard/empty-token semantics for the command allowlist.

    ``None`` (or blank) tokens are tool no-ops (e.g. run_build without a
    target contributes ``"make"``, never an empty string) and pass through.
    An EMPTY allowlist is an explicit deny-all — only wildcard-free explicit
    membership allows a token.
    """
    if token is None or not token.strip():
        return True
    if "*" in allowlist:
        return True
    return token in allowlist


def _command_tokens(tool_name: str, args: Any) -> list[str | None]:
    """Executable tokens a tool call would run, for allowlist matching."""
    if tool_name == "run_build":
        # The build tool always invokes make inside project_dir, so the
        # policy-meaningful token is the TARGET; a default build is "make".
        target = (getattr(args, "target", "") or "").strip()
        return [target or "make"]
    if tool_name == "run_artifact":
        artifact = getattr(args, "artifact_path", "")
        return [Path(artifact).name] if artifact else [None]
    if tool_name == "eco_cli":
        raw = getattr(args, "args", None) or []
        return [raw[0] if raw else None]
    return [None]


def _gate_commands(tool: EcoTool, allowlist: list[str]) -> EcoTool:
    if "*" in allowlist:
        return tool

    def execute(args: Any) -> ToolResult:
        for token in _command_tokens(tool.name, args):
            if not _token_allowed(allowlist, token):
                return ToolResult(
                    content=(
                        f"Permission denied: '{token}' is not in this role's "
                        f"command allowlist ({', '.join(allowlist) or 'empty'})."
                    ),
                    is_error=True,
                    details={"denied": True, "token": token},
                )
        return tool.execute(args)

    return replace(tool, execute=execute)


def apply_role_permissions(
    agent,
    *,
    config: HarnessConfig,
    role: str,
) -> None:
    """Filter + wrap ``agent.tools`` in place according to the role's policy.

    Must run BEFORE the system prompt is assembled so the tool contract the
    model sees matches what it may actually call. Internal backends only —
    see the module docstring for the external-backend limitation.
    """
    role_spec: RoleSpec = config.roles.get(role, RoleSpec())
    perms = role_spec.permissions
    tools = getattr(agent, "tools", None)
    if not isinstance(tools, dict):
        return

    denied = _denied_tools(perms)
    for tool_name in list(tools):
        if tool_name in denied:
            del tools[tool_name]

    for tool_name, tool in list(tools.items()):
        if tool_name in _COMMAND_GATED_TOOLS:
            tools[tool_name] = _gate_commands(tool, list(perms.commands))
