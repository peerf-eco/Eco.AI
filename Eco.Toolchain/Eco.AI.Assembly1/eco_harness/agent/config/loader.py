from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class ModelProfile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    provider: str = "openrouter"
    reasoning: str = "medium"
    temperature: float | None = None
    max_tokens: int | None = None
    # Optional OpenRouter provider pin for this specific model (e.g. "tencent").
    # When set it overrides the global OPENROUTER_PROVIDER_PIN env; when omitted
    # the env default is used. Keeps a model's pin matched to its provider so
    # different roles using different models don't get mismatched pin 404s.
    # NOTE: this is an OpenRouter ROUTING hint (upstream provider slug), not a
    # credential — real secrets (API keys) live in .env and are never part of
    # the config surface.
    provider_pin: str | None = None


class ProviderProfile(BaseModel):
    """A custom LLM endpoint (e.g. a local LM Studio / Ollama / vLLM server).

    Named providers are referenced by ``ModelProfile.provider`` so a model can
    route to a self-hosted inference server instead of OpenRouter. The
    ``base_url`` points at the OpenAI-compatible ``/v1`` root (``http://host:port/v1``);
    ``api_key_env`` selects the env var holding the bearer token (optional for
    most local servers). ``type`` is reserved for future non-openai-compat APIs.

    model_config = extra="ignore" so provider responses with unknown fields
    parse cleanly and a stale workspace key can never crash the loader.
    """

    model_config = ConfigDict(extra="ignore")

    base_url: str
    type: str = "openai-compat"
    api_key_env: str | None = None


class BudgetSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    per_query_tokens: int = 100_000
    per_query_usd: float | None = None
    per_day_usd: float | None = None
    max_iters: int = 40
    max_wall_s: int = 900


class PermissionSpec(BaseModel):
    """What a role is allowed to do, enforced at tool level.

    Booleans gate whole tool groups (the tools are removed from the role's
    toolset before prompt assembly, so the model never sees a denied tool).
    ``commands`` is an allowlist of executable tokens (make target, artifact
    basename, eco-cli subcommand); ``["*"]`` allows everything.

    Granularity is PER-ROLE on purpose: roles are the trust boundary of the
    harness (a tester may run binaries, an architect should not write files),
    while models are interchangeable capability providers. Harness-level
    defaults live in ``HarnessConfig.default_permissions``; per-role entries
    override them.
    """

    model_config = ConfigDict(extra="ignore")

    fs_read: bool = True
    fs_write: bool = True
    build: bool = True
    execute: bool = True
    rag_search: bool = True
    skills: bool = True
    network: bool = True
    commands: list[str] = Field(default_factory=lambda: ["*"])


class RoleSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    backend: str = "internal"
    model: str = "reasoning_heavy"
    reasoning: str = "medium"
    prompt: str | None = None
    skill_versions: dict[str, str] = Field(default_factory=dict)
    tools: list[str] = Field(default_factory=list)
    budgets: BudgetSpec = Field(default_factory=BudgetSpec)
    permissions: PermissionSpec = Field(default_factory=PermissionSpec)


class LanguageSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    prompt: str | None = None
    skill_versions: dict[str, str] = Field(default_factory=dict)
    eco_wizard: str | None = None


class ModeSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    prompt: str
    roles: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)


class HarnessConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    root: Path
    default_language: str = "C"
    default_platform: dict[str, str] = Field(
        default_factory=lambda: {"os": "Linux", "arch": "x86_64"},
    )
    models: dict[str, ModelProfile] = Field(default_factory=dict)
    # User-defined LLM endpoints (local inference servers, self-hosted
    # gateways). Referenced by ModelProfile.provider; absent → OpenRouter.
    providers: dict[str, ProviderProfile] = Field(default_factory=dict)
    roles: dict[str, RoleSpec] = Field(default_factory=dict)
    languages: dict[str, LanguageSpec] = Field(default_factory=dict)
    modes: dict[str, ModeSpec] = Field(default_factory=dict)
    # Harness-level permission defaults; per-role overrides live on RoleSpec.
    default_permissions: PermissionSpec = Field(default_factory=PermissionSpec)
    worktree_root: Path | None = None
    source_max_bytes: int = 300_000
    dynamic_tail_items: int = 5
    # budgets.yaml → retained_tool_outputs: how many newest tool outputs the
    # agent keeps verbatim in context (wired to EcoAgent.max_tool_results in
    # PRD_2 Phase 2; previously a dead key).
    retained_tool_outputs: int = 5
    max_hops: int = 8
    # Architect -> coder handoff size cap (bytes of markdown). The
    # plan_validator BLOCKS the to_coder stop-tool when the plan exceeds
    # this budget; raising it lets the architect hand more context to
    # the coder, lowering it keeps the coder under tight provider
    # context limits (see `chat-1ca5b8f4` Celsius->Fahrenheit
    # post-mortem — the previous behaviour re-stitched the whole
    # architect context into the coder prompt and crashed a 262K
    # provider limit).
    plan_handoff_max_bytes: int = 8_192
    source_roots: list[Path] = Field(default_factory=list)
    eco_wizard_path: str | None = None
    eco_cli_path: str | None = None
    workspace_override: Path | None = None


def _project_root(root: Path | None) -> Path:
    if root is not None:
        return Path(root).resolve()
    from eco_harness.agent.internal.tools.paths import (
        PACKAGE_ROOT,
        is_dev_checkout,
        repo_root,
    )

    # Dev checkout: config/ lives at the repo root. Installed wheel: config/
    # ships as package data inside eco_harness/.
    return repo_root() if is_dev_checkout() else PACKAGE_ROOT


def _config_root(project_root: Path) -> Path:
    """config/ dir for the given project root, falling back to the package
    copy when the caller's root has none (installed mode with a custom
    ECO_HOME-style root)."""
    from eco_harness.agent.internal.tools.paths import PACKAGE_ROOT

    local = project_root / "config"
    if local.is_dir() or project_root == PACKAGE_ROOT:
        return local
    packaged = PACKAGE_ROOT / "config"
    if packaged.is_dir():
        return packaged
    return local


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def load_marketplace_framework_components(root: Path | None = None) -> tuple[str, ...]:
    """config/marketplace.yaml → framework_components (wired in PRD_2 Phase 2).

    These are the always-required components ``_prepull_framework`` copies
    into every project_dir. Falls back to the historical hard-coded set when
    the key is absent.
    """
    config_root = _config_root(_project_root(root))
    marketplace = _read_yaml(config_root / "marketplace.yaml")
    components = marketplace.get("framework_components")
    if isinstance(components, list) and all(isinstance(c, str) for c in components):
        return tuple(components)
    return (
        "Eco.Core1", "Eco.InterfaceBus1", "Eco.MemoryManager1",
        "Eco.FileSystemManagement1", "Eco.System1",
    )


def _role_files(config_root: Path) -> dict[str, dict[str, Any]]:
    roles = _read_yaml(config_root / "roles.yaml").get("roles", {})
    if not isinstance(roles, dict):
        return {}
    return roles


def _resolve_permissions(*layers: Any) -> PermissionSpec:
    """Merge permission layers key-by-key (later layers win).

    Only keys that are actual PermissionSpec fields are considered, so a typo
    or a stale workspace key can neither crash the loader nor silently become
    part of the policy.
    """
    known = set(PermissionSpec.model_fields)
    merged: dict[str, Any] = {}
    for layer in layers:
        if isinstance(layer, dict):
            merged.update({key: value for key, value in layer.items() if key in known})
    return PermissionSpec(**merged)


def load_config(root: Path | None = None) -> HarnessConfig:
    project_root = _project_root(root)
    config_root = _config_root(project_root)
    harness = _read_yaml(config_root / "harness.yaml")
    budgets = _read_yaml(config_root / "budgets.yaml")
    models = _read_yaml(config_root / "models.yaml").get("models", {})
    languages = _read_yaml(config_root / "languages.yaml").get("languages", {})
    modes = _read_yaml(config_root / "modes.yaml").get("modes", {})
    roles = _role_files(config_root)
    if os.getenv("ECO_HARNESS_WORKSPACE_CONFIG"):
        workspace_path = Path(os.environ["ECO_HARNESS_WORKSPACE_CONFIG"])
    else:
        # Dev checkout: workspace overrides live in <repo>/.eco-harness/.
        # Installed wheel: the app home owns user state (no repo to write to).
        from eco_harness.agent.internal.tools.paths import eco_home, is_dev_checkout

        workspace_path = (
            project_root / ".eco-harness" / "workspace.yaml"
            if is_dev_checkout()
            else eco_home() / "workspace.yaml"
        )
    workspace = _read_yaml(workspace_path)
    merged_roles = deepcopy(roles)
    for role_name, workspace_role in workspace.get("roles", {}).items():
        if not isinstance(workspace_role, dict):
            continue
        base_role = merged_roles.get(role_name, {})
        if not isinstance(base_role, dict):
            base_role = {}
        merged_role = {**base_role, **workspace_role}
        base_budget = base_role.get("budgets", {})
        workspace_budget = workspace_role.get("budgets", {})
        if isinstance(base_budget, dict) and isinstance(workspace_budget, dict):
            merged_role["budgets"] = {**base_budget, **workspace_budget}
        merged_roles[role_name] = merged_role
    merged_harness = dict(harness)
    merged_harness.update(workspace.get("harness", {}))
    # Workspace model registry: user-defined/overridden profiles win per key,
    # so a workspace entry can tweak one field (e.g. reasoning) of a repo
    # profile or declare a brand-new named profile for the settings UI.
    # A ``null`` entry REMOVES the profile (how the settings UI deletes a
    # repo-provided model); the "default" profile is always re-created below
    # from LLM_MODEL/env when missing, so deleting it resets to the env model.
    workspace_models = workspace.get("models", {})
    if isinstance(workspace_models, dict):
        models = deepcopy(models)
        for model_name, profile in workspace_models.items():
            if profile is None:
                models.pop(model_name, None)
                continue
            if not isinstance(profile, dict):
                continue
            base_profile = models.get(model_name)
            base_profile = base_profile if isinstance(base_profile, dict) else {}
            models[model_name] = {**base_profile, **profile}
    # Workspace LLM providers: user-defined endpoints referenced by
    # ModelProfile.provider. A ``null`` entry REMOVES the provider. Parsed
    # through ProviderProfile so a malformed entry is skipped (extra="ignore")
    # rather than crashing the whole config load.
    workspace_providers = workspace.get("providers", {})
    provider_profiles: dict[str, ProviderProfile] = {}
    if isinstance(workspace_providers, dict):
        for name, entry in workspace_providers.items():
            if not isinstance(entry, dict) or not entry.get("base_url"):
                continue
            try:
                provider_profiles[name] = ProviderProfile(**entry)
            except Exception:
                # Drop a malformed provider rather than poisoning the load.
                pass

    # Workspace permissions: defaults + per-role deltas. Resolution chain per
    # role (later wins, key-by-key over PermissionSpec fields only):
    #   code defaults < workspace defaults < repo roles.yaml role baseline
    #   < workspace per-role delta
    # The repo per-role baseline is MORE SPECIFIC than the workspace defaults,
    # so it must be applied after them (a global workspace default cannot
    # silently re-enable what roles.yaml restricted for one role).
    workspace_permissions = workspace.get("permissions", {})
    if not isinstance(workspace_permissions, dict):
        workspace_permissions = {}
    permission_defaults_layer = workspace_permissions.get("defaults")
    permission_defaults_layer = (
        permission_defaults_layer if isinstance(permission_defaults_layer, dict) else {}
    )
    workspace_role_permissions = workspace_permissions.get("roles", {})
    if not isinstance(workspace_role_permissions, dict):
        workspace_role_permissions = {}
    workspace_languages = workspace.get("languages", {})
    if isinstance(workspace_languages, dict):
        languages = deepcopy(languages)
        for language_name, workspace_language in workspace_languages.items():
            if not isinstance(workspace_language, dict):
                continue
            base_language = languages.get(language_name, {})
            if not isinstance(base_language, dict):
                base_language = {}
            merged_language = {**base_language, **workspace_language}
            base_skills = base_language.get("skill_versions", {})
            workspace_skills = workspace_language.get("skill_versions", {})
            if isinstance(base_skills, dict) and isinstance(workspace_skills, dict):
                merged_language["skill_versions"] = {**base_skills, **workspace_skills}
            languages[language_name] = merged_language

    env_model = os.getenv("LLM_MODEL")
    if env_model:
        models = dict(models)
        models.setdefault("default", {})
        models["default"] = {**models["default"], "id": env_model}
    for role_name, role in merged_roles.items():
        if not isinstance(role, dict):
            continue
        env_prefix = f"ECO_ROLE_{role_name.upper()}_"
        env_tokens = os.getenv(env_prefix + "MAX_TOKENS")
        if env_tokens:
            role.setdefault("budgets", {})["per_query_tokens"] = int(env_tokens)

    for role_name, role in merged_roles.items():
        if not isinstance(role, dict):
            continue
        env_prefix = f"ECO_ROLE_{role_name.upper()}_"
        role["backend"] = os.getenv(env_prefix + "BACKEND", role.get("backend", "internal"))
        role["model"] = os.getenv(env_prefix + "MODEL", role.get("model", "default"))
        role["reasoning"] = os.getenv(
            env_prefix + "REASONING",
            role.get("reasoning", "medium"),
        )

    model_profiles = {
        name: ModelProfile(**profile)
        for name, profile in models.items()
        if isinstance(profile, dict) and profile.get("id")
    }
    if "default" not in model_profiles:
        model_profiles["default"] = ModelProfile(
            id=os.getenv("LLM_MODEL", "tencent/hy3-preview"),
        )
    role_specs = {
        name: RoleSpec(**value)
        for name, value in merged_roles.items()
        if isinstance(value, dict)
    }
    for role_name, role_spec in role_specs.items():
        role_spec.permissions = _resolve_permissions(
            permission_defaults_layer,
            # Repo roles.yaml may carry a per-role baseline in the role dict
            # itself; it outranks the workspace-wide defaults above.
            merged_roles[role_name].get("permissions"),
            workspace_role_permissions.get(role_name),
        )
    language_specs = {
        name: LanguageSpec(**value)
        for name, value in languages.items()
        if isinstance(value, dict)
    }
    mode_specs = {
        name: ModeSpec(**value)
        for name, value in modes.items()
        if isinstance(value, dict)
    }
    return HarnessConfig(
        root=project_root,
        models=model_profiles,
        providers=provider_profiles,
        roles=role_specs,
        languages=language_specs,
        modes=mode_specs,
        default_permissions=_resolve_permissions(permission_defaults_layer),
        worktree_root=(
            Path(
                os.getenv(
                    "ECO_WORKTREE_ROOT",
                    merged_harness.get("worktree_root", ""),
                ),
            ).resolve()
            if os.getenv("ECO_WORKTREE_ROOT", merged_harness.get("worktree_root", ""))
            else None
        ),
        source_max_bytes=int(
            os.getenv("HARNESS_SOURCE_MAX_BYTES", merged_harness.get("source_max_bytes", 300_000)),
        ),
        dynamic_tail_items=int(
            os.getenv("HARNESS_DYNAMIC_TAIL_ITEMS", merged_harness.get("dynamic_tail_items", 5)),
        ),
        retained_tool_outputs=int(
            os.getenv(
                "HARNESS_RETAINED_TOOL_OUTPUTS",
                budgets.get("retained_tool_outputs", 5),
            ),
        ),
        max_hops=int(
            os.getenv("HARNESS_MAX_HOPS", merged_harness.get("max_hops", 8)),
        ),
        plan_handoff_max_bytes=int(
            os.getenv(
                "HARNESS_PLAN_HANDOFF_MAX_BYTES",
                merged_harness.get("plan_handoff_max_bytes", 8_192),
            ),
        ),
        # Only keep source roots that EXIST: in installed mode the config
        # defaults resolve under site-packages where they are absent, and a
        # truthy-but-junk list would defeat the roles.py fallback to the
        # resolved marketplace cache (losing the Eco.Core1 prompt stitch).
        source_roots=[
            resolved
            for resolved in (
                (project_root / value if not Path(value).is_absolute() else Path(value)).resolve()
                for value in merged_harness.get(
                    "source_roots",
                    ["source", "marketplace_cache"],
                )
            )
            if resolved.exists()
        ],
        default_language=os.getenv(
            "DEFAULT_LANGUAGE",
            merged_harness.get("default_language", "C"),
        ),
        default_platform=merged_harness.get(
            "default_platform",
            {"os": "Linux", "arch": "x86_64"},
        ),
        eco_wizard_path=os.getenv(
            "ECO_WIZARD_PATH",
            merged_harness.get("eco_wizard_path"),
        ),
        eco_cli_path=os.getenv("ECO_CLI_PATH", merged_harness.get("eco_cli_path")),
        workspace_override=workspace_path,
    )


def load_role_config(role: str, root: Path | None = None) -> tuple[HarnessConfig, RoleSpec, ModelProfile]:
    config = load_config(root)
    spec = config.roles.get(role, RoleSpec())
    profile = config.models.get(spec.model)
    if profile is None and "/" in spec.model:
        profile = ModelProfile(id=spec.model)
    profile = profile or config.models["default"]
    if spec.reasoning != profile.reasoning:
        profile = profile.model_copy(update={"reasoning": spec.reasoning})
    return config, spec, profile