from __future__ import annotations

import os
from pathlib import Path

from eco_harness.agent.config.loader import HarnessConfig, RoleSpec
from eco_harness.agent.context.customization import (
    on_demand_skills,
    resolve_custom_instructions,
)
from eco_harness.agent.context.assembler import build_static_system_prompt
from eco_harness.agent.pi_ai import SimpleStreamOptions
from eco_harness.adapters.eco_agent_bridge import ExternalEcoAgent
from eco_harness.adapters.factory import make_external_backend
from eco_harness.permissions import apply_role_permissions


def _backend_name(spec: RoleSpec) -> str:
    return spec.backend.removesuffix("_cli")


def _language_prompt(config: HarnessConfig, language: str) -> str:
    language_spec = config.languages.get(language)
    configured_prompt = language_spec.prompt if language_spec else None
    path = (
        config.root / "config" / configured_prompt
        if configured_prompt
        else config.root / "config" / "prompts" / "languages" / f"{language}.md"
    )
    if not path.exists():
        return (
            f"=== SELECTED LANGUAGE ===\n{language}\n"
            "Use the language-specific conventions configured by the operator."
        )
    return path.read_text(encoding="utf-8")


def _mode_prompt(config: HarnessConfig, mode: str) -> str:
    mode_spec = config.modes.get(mode)
    if mode_spec is None:
        raise ValueError(f"Unsupported mode: {mode}")
    path = config.root / "config" / mode_spec.prompt
    if not path.exists():
        raise FileNotFoundError(f"Mode prompt was not found: {path}")
    return path.read_text(encoding="utf-8")


def _workspace_prompt(config: HarnessConfig, role: str) -> Path | None:
    """Workspace-level override location for a role prompt.

    ``<workspace>/prompts/<role>.md`` next to workspace.yaml (by default
    ``.eco-harness/prompts/<role>.md``). Wins over config/prompts so an
    operator can specialize a role without touching repository config.
    """
    if config.workspace_override is None:
        return None
    return config.workspace_override.parent / "prompts" / f"{role}.md"


def _read_prompt(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _role_prompt(config: HarnessConfig, role: str, fallback: str) -> str:
    """Resolve the role prompt: workspace > config/prompts > built-in.

    Empty or unreadable files are treated as absent, so a placeholder file can
    never silently blank out the built-in instructions (regression: the old
    self-referential coder.md/tester.md stubs replaced the full workflow
    prompts — see PRD_2.md).
    """
    candidates: list[Path] = []
    workspace_path = _workspace_prompt(config, role)
    if workspace_path is not None:
        candidates.append(workspace_path)
    role_spec = config.roles.get(role)
    if role_spec and role_spec.prompt:
        candidates.append(config.root / "config" / role_spec.prompt)
    for path in candidates:
        content = _read_prompt(path)
        if content:
            return content
    return fallback


def _tool_contract(agent) -> str:
    tools = getattr(agent, "tools", {})
    return "\n".join(
        f"- {name}: {tool.description}"
        for name, tool in sorted(tools.items())
    )


def _merged_skill_versions(config: HarnessConfig, role: str, language: str) -> dict[str, str]:
    """Language skill map merged under the role's map (same order as prompts)."""
    role_spec = config.roles.get(role, RoleSpec())
    language_spec = config.languages.get(language)
    language_skills = language_spec.skill_versions if language_spec else {}
    return {**language_skills, **role_spec.skill_versions}


def _wire_on_demand_skill_tool(
    agent,
    *,
    config: HarnessConfig,
    role: str,
    language: str,
) -> None:
    """Attach read_skill when this role's merged map references dynamic skills.

    Dynamic = SKILL.md with YAML frontmatter (see
    agent/context/customization.py). The tool must be attached BEFORE the
    static prompt is built so the tool contract lists it.
    """
    tools = getattr(agent, "tools", None)
    if not isinstance(tools, dict):
        return
    refs = on_demand_skills(
        project_root=config.root,
        skill_versions=_merged_skill_versions(config, role, language),
    )
    if refs and "read_skill" not in tools:
        from eco_harness.agent.internal.tools.skill_reader import make_read_skill_tool

        tools["read_skill"] = make_read_skill_tool(project_root=config.root)


def _static_prompt(
    *,
    config: HarnessConfig,
    role: str,
    role_prompt: str,
    language: str,
    project_dir: Path,
    marketplace_cache_root: Path,
    tool_contract: str = "",
    mode: str = "create",
) -> str:
    role_spec = config.roles.get(role, RoleSpec())
    custom, _dynamic = resolve_custom_instructions(
        project_root=config.root,
        role=role,
        language=language,
        skill_versions=_merged_skill_versions(config, role, language),
    )
    role_prompt = (
        f"=== MODE: {mode.upper()} ===\n{_mode_prompt(config, mode)}\n\n"
        f"{role_prompt}\n\n"
        f"{_language_prompt(config, language)}\n\n"
        f"{custom}\n\n"
        f"=== ROLE CONFIGURATION ===\nbackend={role_spec.backend}\n"
        f"model={role_spec.model}\nreasoning={role_spec.reasoning}"
    )
    return build_static_system_prompt(
        role_prompt,
        source_roots=(
            config.source_roots
            or [marketplace_cache_root]
        ),
        tool_contract=tool_contract,
        max_source_bytes=config.source_max_bytes,
        core1_files=config.core1_stitch_files,
    )


def _configure_context(
    agent,
    *,
    config: HarnessConfig,
    role: str,
    language: str,
    project_dir: Path,
    marketplace_cache_root: Path,
    mode: str = "create",
) -> None:
    role_spec = config.roles.get(role, RoleSpec())
    agent.system_prompt = _static_prompt(
        config=config,
        role=role,
        role_prompt=getattr(agent, "system_prompt", ""),
        language=language,
        project_dir=project_dir,
        marketplace_cache_root=marketplace_cache_root,
        tool_contract=_tool_contract(agent),
        mode=mode,
    )
    agent.max_iters = role_spec.budgets.max_iters
    # budgets.yaml → retained_tool_outputs (PRD_2 Phase 2 wired this dead key).
    agent.max_tool_results = config.retained_tool_outputs
    if hasattr(agent, "stream_options"):
        model_profile = config.models.get(role_spec.model)
        max_tokens = model_profile.max_tokens if model_profile else None
        if max_tokens is None:
            max_tokens = role_spec.budgets.per_query_tokens
        agent.stream_options = SimpleStreamOptions(
            reasoning=role_spec.reasoning,
            maxTokens=max_tokens,
        )


def make_role_agent(
    role: str,
    *,
    config: HarnessConfig,
    model,
    cli_path: Path | None,
    project_dir: Path,
    make_exe: Path,
    language: str,
    marketplace_cache_root: Path,
    on_event=None,
    trace_dir: Path | None = None,
    mode: str = "create",
    pipeline: bool = False,
):
    role_spec = config.roles.get(role, RoleSpec())
    backend_name = _backend_name(role_spec)
    if config.eco_wizard_path:
        os.environ.setdefault("ECO_WIZARD_PATH", config.eco_wizard_path)
    if config.eco_cli_path:
        os.environ.setdefault("ECO_CLI_PATH", config.eco_cli_path)
    if backend_name not in {"internal", "builtin", "eco"}:
        backend = make_external_backend(
            backend_name,
            cwd=project_dir,
            timeout_s=role_spec.budgets.max_wall_s,
        )
        # Prompt parity (PRD_2 Phase 2): external coders/testers get the same
        # config/prompts/<role>.md content as internal agents — the placeholder
        # one-liner used to silently drop the STEP workflow and stop-tool
        # discipline for every external backend (pi/claude/codex/grok).
        return ExternalEcoAgent(
            backend=backend,
            role=role,
            max_wall_s=role_spec.budgets.max_wall_s,
            system_prompt=_static_prompt(
                config=config,
                role=role,
                role_prompt=_role_prompt(
                    config,
                    role,
                    f"You are the {role} role in the ACOM meta-harness.",
                ),
                language=language,
                project_dir=project_dir,
                marketplace_cache_root=marketplace_cache_root,
                mode=mode,
            ),
            on_event=on_event,
        )

    if role == "architect":
        from eco_harness.agent.internal.agents.architect import make_architect
        agent = make_architect(
            model=model,
            cli_path=cli_path,
            project_dir=project_dir,
            max_iters=role_spec.budgets.max_iters,
            trace_dir=trace_dir,
            on_event=on_event,
        )
    elif role == "coder":
        from eco_harness.agent.internal.agents.coder import make_coder
        agent = make_coder(
            model=model,
            project_dir=project_dir,
            make_exe=make_exe,
            max_iters=role_spec.budgets.max_iters,
            trace_dir=trace_dir,
            on_event=on_event,
        )
    elif role == "tester":
        from eco_harness.agent.internal.agents.tester import make_tester
        agent = make_tester(
            model=model,
            project_dir=project_dir,
            max_iters=role_spec.budgets.max_iters,
            trace_dir=trace_dir,
            on_event=on_event,
        )
    elif role == "reviewer":
        from eco_harness.agent.internal.agents.reviewer import make_reviewer
        agent = make_reviewer(
            model=model,
            project_dir=project_dir,
            max_iters=role_spec.budgets.max_iters,
            trace_dir=trace_dir,
            on_event=on_event,
            pipeline=pipeline,
        )
    else:
        raise ValueError(f"Unsupported role: {role}")
    agent.system_prompt = _role_prompt(config, role, agent.system_prompt)
    # On-demand skills: attach the fetch tool before prompt assembly so the
    # tool contract includes it (external backends skip this — their manifest
    # entries carry source paths for their own file tools).
    _wire_on_demand_skill_tool(agent, config=config, role=role, language=language)
    # Permission policy (settings panel → workspace.yaml): denied tool groups
    # are dropped and execution tools get the command allowlist — both BEFORE
    # prompt assembly so the tool contract matches the enforced toolset.
    apply_role_permissions(agent, config=config, role=role)
    _configure_context(
        agent,
        config=config,
        role=role,
        language=language,
        project_dir=project_dir,
        marketplace_cache_root=marketplace_cache_root,
        mode=mode,
    )
    return agent
