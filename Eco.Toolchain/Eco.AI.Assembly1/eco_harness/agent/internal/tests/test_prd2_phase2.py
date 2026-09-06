"""PRD_2.md Phase 2 regression tests.

Locks in the consistency work:

1. Single binary-resolution policy (`agent/internal/tools/binaries.py`).
2. Skills cleanup: phantom `language` key gone from YAML skill_versions;
   language profiles resolve without it.
3. Dead-YAML wiring: marketplace.yaml.framework_components,
   budgets.yaml.retained_tool_outputs, config/agents/external/*.yaml flags.
4. External-role prompt parity with internal agents.
5. build_pipeline / server topology convergence constants.
"""
from __future__ import annotations

import os
from pathlib import Path

from eco_harness.agent.config.loader import (
    load_config,
    load_marketplace_framework_components,
)
from eco_harness.agent.internal.entry import EXECUTION_EDGES, EXECUTION_ENTRY, PIPELINE_EDGES
from eco_harness.agent.internal.tools import binaries
from eco_harness.agent.pi_ai import Model, ModelCost
from eco_harness.adapters.factory import make_external_backend
from eco_harness.roles import make_role_agent


# ── 1. Binary resolution order ────────────────────────────────────────────────


def test_resolve_binary_explicit_wins(tmp_path: Path, monkeypatch):
    candidate = tmp_path / "custom" / "eco-cli"
    candidate.parent.mkdir(parents=True)
    candidate.touch()
    resolved = binaries.resolve_binary("eco-cli", repo=tmp_path, explicit=candidate)
    assert resolved == candidate


def test_resolve_binary_env_before_bin(tmp_path: Path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "eco-cli").touch()
    env_dir = tmp_path / "env"
    env_dir.mkdir()
    env_binary = env_dir / "eco-cli"
    env_binary.touch()
    monkeypatch.setenv("ECO_CLI_PATH", str(env_binary))
    assert binaries.resolve_binary("eco-cli", repo=tmp_path) == env_binary


def test_resolve_binary_canonical_bin_home(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("ECO_CLI_PATH", raising=False)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    binary = bin_dir / "eco-cli"
    binary.touch()
    assert binaries.resolve_binary("eco-cli", repo=tmp_path) == binary


def test_resolve_binary_ignores_legacy_siblings(tmp_path: Path, monkeypatch):
    """Deprecated <repo>/<name>-{linux,windows}/ sibling dirs are not probed."""
    monkeypatch.delenv("ECO_CLI_PATH", raising=False)
    sibling = tmp_path / "eco-cli-linux" / "eco-cli"
    sibling.parent.mkdir(parents=True)
    sibling.touch()
    assert binaries.resolve_binary("eco-cli", repo=tmp_path) is None


def test_resolve_binary_windows_exe_suffix(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("ECO_CLI_PATH", raising=False)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    binary = bin_dir / "eco-cli.exe"
    binary.touch()
    monkeypatch.setattr(binaries.sys, "platform", "win32")
    assert binaries.resolve_binary("eco-cli", repo=tmp_path) == binary


def test_resolve_binary_none_when_missing(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("ECO_CLI_PATH", raising=False)
    assert binaries.resolve_binary("definitely-not-a-tool", repo=tmp_path) is None


# ── 2. Phantom `language` skill key removed ──────────────────────────────────


def test_no_phantom_language_skill_key():
    cfg = load_config()
    for name, spec in cfg.roles.items():
        assert "language" not in spec.skill_versions, f"role {name}"
    for name, spec in cfg.languages.items():
        assert "language" not in spec.skill_versions, f"language {name}"


# ── 3. Dead-YAML wiring ──────────────────────────────────────────────────────


def test_framework_components_read_from_marketplace_yaml():
    components = load_marketplace_framework_components(Path(__file__).resolve().parents[3])
    assert "Eco.Core1" in components
    assert "Eco.System1" in components
    # Matches the shipped marketplace.yaml list.
    assert set(components) == {
        "Eco.Core1",
        "Eco.InterfaceBus1",
        "Eco.MemoryManager1",
        "Eco.FileSystemManagement1",
        "Eco.System1",
    }


def test_framework_components_fallback_without_yaml(tmp_path: Path):
    components = load_marketplace_framework_components(tmp_path)
    assert "Eco.Core1" in components


def test_retained_tool_outputs_loaded_from_budgets_yaml():
    cfg = load_config()
    # budgets.yaml ships retained_tool_outputs: 5; loader must surface it.
    assert cfg.retained_tool_outputs >= 1


def test_max_tool_results_uses_retained_tool_outputs(tmp_path: Path):
    cfg = load_config()
    model = Model(
        id="scripted", name="scripted", api="faux-scripted",
        provider="scripted", baseUrl="", cost=ModelCost(),
    )
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    agent = make_role_agent(
        "coder",
        config=cfg,
        model=model,
        cli_path=None,
        project_dir=project_dir,
        make_exe=Path("make"),
        language="C",
        marketplace_cache_root=cfg.root / "marketplace_cache",
        mode="auto",
    )
    assert agent.max_tool_results == cfg.retained_tool_outputs


def test_external_backend_flag_from_agent_yaml(monkeypatch):
    monkeypatch.delenv("ECO_GROK_PATH", raising=False)
    backend = make_external_backend("grok")
    # grok's flag only exists in config/agents/external/grok.yaml — the old
    # hard-coded _FLAGS dict did not contain grok at all.
    assert backend.flag == "-p"


# ── 4. External-role prompt parity ───────────────────────────────────────────


def test_external_role_gets_config_prompt(tmp_path: Path, monkeypatch):
    """A pi-backed coder sees the same STEP workflow as an internal coder."""
    monkeypatch.delenv("ECO_ROLE_CODER_BACKEND", raising=False)
    monkeypatch.setenv("ECO_ROLE_CODER_BACKEND", "pi")
    monkeypatch.delenv("ECO_PI_PATH", raising=False)
    cfg = load_config()
    model = Model(
        id="scripted", name="scripted", api="faux-scripted",
        provider="scripted", baseUrl="", cost=ModelCost(),
    )
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    agent = make_role_agent(
        "coder",
        config=cfg,
        model=None,
        cli_path=None,
        project_dir=project_dir,
        make_exe=Path("make"),
        language="C",
        marketplace_cache_root=cfg.root / "marketplace_cache",
        mode="auto",
    )
    from eco_harness.adapters.eco_agent_bridge import ExternalEcoAgent

    assert isinstance(agent, ExternalEcoAgent)
    # Content of config/prompts/coder.md — not the placeholder one-liner.
    assert "STEP 1" in agent.system_prompt
    assert "You are the coder role in the ACOM meta-harness." != agent.system_prompt


# ── 5. Pipeline topology convergence ─────────────────────────────────────────


def test_execution_edges_is_pipeline_edges_with_architect_cut():
    for role, edges in PIPELINE_EDGES.items():
        if role not in EXECUTION_EDGES:
            continue
        for edge, target in edges.items():
            expected = None if edge == "to_architect" else target
            assert EXECUTION_EDGES[role][edge] == expected


def test_execution_entry_is_coder():
    assert EXECUTION_ENTRY == "coder"


def test_build_pipeline_accepts_trace_dir(tmp_path: Path):
    from eco_harness.agent.internal.entry import build_pipeline

    model = Model(
        id="scripted", name="scripted", api="faux-scripted",
        provider="scripted", baseUrl="", cost=ModelCost(),
    )
    trace_dir = tmp_path / "traces"
    orch = build_pipeline(
        model=model,
        cli_path=None,
        project_dir=tmp_path / "proj",
        make_exe=Path("make"),
        trace_dir=trace_dir,
    )
    assert set(orch.agents) == {"architect", "coder", "tester"}
