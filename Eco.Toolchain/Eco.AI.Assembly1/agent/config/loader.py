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


class BudgetSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    per_query_tokens: int = 100_000
    per_query_usd: float | None = None
    per_day_usd: float | None = None
    max_iters: int = 40
    max_wall_s: int = 900


class RoleSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    backend: str = "internal"
    model: str = "reasoning_heavy"
    reasoning: str = "medium"
    prompt: str | None = None
    skill_versions: dict[str, str] = Field(default_factory=dict)
    tools: list[str] = Field(default_factory=list)
    budgets: BudgetSpec = Field(default_factory=BudgetSpec)


class LanguageSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    prompt: str | None = None
    skill_versions: dict[str, str] = Field(default_factory=dict)
    eco_wizard: str | None = None


class HarnessConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    root: Path
    default_language: str = "C"
    default_platform: dict[str, str] = Field(
        default_factory=lambda: {"os": "Linux", "arch": "x86_64"},
    )
    models: dict[str, ModelProfile] = Field(default_factory=dict)
    roles: dict[str, RoleSpec] = Field(default_factory=dict)
    languages: dict[str, LanguageSpec] = Field(default_factory=dict)
    source_max_bytes: int = 300_000
    dynamic_tail_items: int = 5
    max_hops: int = 8
    source_roots: list[Path] = Field(default_factory=list)
    eco_wizard_path: str | None = None
    eco_cli_path: str | None = None
    workspace_override: Path | None = None


def _project_root(root: Path | None) -> Path:
    return (root or Path(__file__).resolve().parents[2]).resolve()


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _role_files(config_root: Path) -> dict[str, dict[str, Any]]:
    roles = _read_yaml(config_root / "roles.yaml").get("roles", {})
    if not isinstance(roles, dict):
        return {}
    return roles


def load_config(root: Path | None = None) -> HarnessConfig:
    project_root = _project_root(root)
    config_root = project_root / "config"
    harness = _read_yaml(config_root / "harness.yaml")
    models = _read_yaml(config_root / "models.yaml").get("models", {})
    languages = _read_yaml(config_root / "languages.yaml").get("languages", {})
    roles = _role_files(config_root)
    workspace_path = Path(
        os.getenv(
            "ECO_HARNESS_WORKSPACE_CONFIG",
            str(project_root / ".eco-harness" / "workspace.yaml"),
        ),
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
            id=os.getenv("LLM_MODEL", "moonshotai/kimi-k2-thinking"),
        )
    role_specs = {
        name: RoleSpec(**value)
        for name, value in merged_roles.items()
        if isinstance(value, dict)
    }
    language_specs = {
        name: LanguageSpec(**value)
        for name, value in languages.items()
        if isinstance(value, dict)
    }
    return HarnessConfig(
        root=project_root,
        models=model_profiles,
        roles=role_specs,
        languages=language_specs,
        source_max_bytes=int(
            os.getenv("HARNESS_SOURCE_MAX_BYTES", merged_harness.get("source_max_bytes", 300_000)),
        ),
        dynamic_tail_items=int(
            os.getenv("HARNESS_DYNAMIC_TAIL_ITEMS", merged_harness.get("dynamic_tail_items", 5)),
        ),
        max_hops=int(
            os.getenv("HARNESS_MAX_HOPS", merged_harness.get("max_hops", 8)),
        ),
        source_roots=[
            (
                project_root / value
                if not Path(value).is_absolute()
                else Path(value)
            ).resolve()
            for value in merged_harness.get(
                "source_roots",
                ["source", "marketplace_cache"],
            )
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