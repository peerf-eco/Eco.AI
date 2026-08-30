"""PRD_2.md Phase 0 regression tests.

Locks in the desired behavior for the three audit bugs fixed in Phase 1:

1. External bridge event marshalling — the pre-fix code imported the event
   enum from a retired versioned module path and crashed every role
   configured with an external backend (pi / claude / codex / grok) the
   moment events were wired.
2. Prompt precedence — placeholder config/prompts/coder.md and tester.md
   stubs used to overwrite the full built-in workflow prompts.
3. Host-mode artifact resolution — hard-coded /app defaults broke host
   runs (search_marketplace FileNotFoundError, grep whitelist missing the
   cache).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from agent.config.loader import HarnessConfig, RoleSpec, load_config
from agent.internal.eco_agent import EventType
from agent.internal.tools import paths as tool_paths
from agent.pi_ai import Model, ModelCost
from eco_harness.adapters.eco_agent_bridge import ExternalEcoAgent
from eco_harness.adapters.external_cli import ExternalCliBackend
from eco_harness.adapters.protocol import AgentResult
from eco_harness.roles import _role_prompt, make_role_agent


# ── 1. External bridge event marshalling ─────────────────────────────────────


class _ScriptedBackend(ExternalCliBackend):
    """External CLI backend stand-in: emits canned events, returns canned result."""

    def __init__(self, events: list[dict], result: AgentResult):
        super().__init__("pi", cwd=None)
        self._events = events
        self._result = result
        self.captured_seed: str | None = None

    def run(self, *, role, seed, budget, on_event=None):  # noqa: ANN001
        self.captured_seed = seed
        for event in self._events:
            if on_event:
                on_event(event)
        return self._result


def _bridge(events: list[dict], result: AgentResult, on_event) -> tuple[ExternalEcoAgent, _ScriptedBackend]:
    backend = _ScriptedBackend(events, result)
    agent = ExternalEcoAgent(
        backend=backend,
        role="coder",
        max_wall_s=60,
        system_prompt="STATIC PROMPT",
        on_event=on_event,
    )
    return agent, backend


def test_bridge_emits_events_without_import_error():
    """The versioned-import crash: events flow through on_event, run completes."""
    events: list = []
    agent, _ = _bridge(
        events=[
            {"type": "start", "role": "coder"},
            {"type": "totally-unknown-kind"},
            {"type": "done", "edge": "done"},
        ],
        result=AgentResult(status="done", edge="done", message="ok"),
        on_event=events.append,
    )
    result = agent.run("do the task")
    assert result.status == "done"
    assert result.stop_tool_name == "done"
    types = [e.type for e in events]
    assert EventType.START in types
    # Unknown event types degrade to ERROR instead of raising.
    assert EventType.ERROR in types
    assert EventType.DONE in types


def test_bridge_seed_carries_static_prompt():
    """External CLIs have no system-prompt API — static prompt rides in the seed."""
    agent, backend = _bridge(
        events=[],
        result=AgentResult(status="done", edge="done", message="ok"),
        on_event=lambda _e: None,
    )
    agent.run("task")
    assert backend.captured_seed is not None
    assert "STATIC PROMPT" in backend.captured_seed
    assert "=== DYNAMIC SEED ===" in backend.captured_seed


def test_bridge_survives_broken_on_event():
    """Event-sink failures are logged-and-dropped, never kill the run."""
    def broken(_event):
        raise RuntimeError("sink exploded")

    agent, _ = _bridge(
        events=[{"type": "start"}, {"type": "done", "edge": "done"}],
        result=AgentResult(status="done", edge="done", message="ok"),
        on_event=broken,
    )
    result = agent.run("task")
    assert result.status == "done"


def test_bridge_maps_backend_error_status():
    agent, _ = _bridge(
        events=[],
        result=AgentResult(status="error", edge=None, message="", error="pi exited with code 1"),
        on_event=lambda _e: None,
    )
    result = agent.run("task")
    assert result.status == "error"
    assert "pi exited" in (result.error or "")


# ── 2. Prompt precedence: workspace > config/prompts > built-in ─────────────


def _synthetic_config(tmp_path: Path) -> HarnessConfig:
    cfg = HarnessConfig(
        root=tmp_path,
        workspace_override=tmp_path / ".eco-harness" / "workspace.yaml",
    )
    cfg.roles["coder"] = RoleSpec(prompt="prompts/coder.md")
    return cfg


def test_role_prompt_builtin_fallback(tmp_path: Path):
    cfg = _synthetic_config(tmp_path)
    assert _role_prompt(cfg, "coder", "BUILTIN") == "BUILTIN"


def test_role_prompt_config_level(tmp_path: Path):
    cfg = _synthetic_config(tmp_path)
    prompts = tmp_path / "config" / "prompts"
    prompts.mkdir(parents=True)
    (prompts / "coder.md").write_text("CONFIG LEVEL", encoding="utf-8")
    assert _role_prompt(cfg, "coder", "BUILTIN") == "CONFIG LEVEL"


def test_role_prompt_workspace_wins(tmp_path: Path):
    cfg = _synthetic_config(tmp_path)
    prompts = tmp_path / "config" / "prompts"
    prompts.mkdir(parents=True)
    (prompts / "coder.md").write_text("CONFIG LEVEL", encoding="utf-8")
    ws_prompts = tmp_path / ".eco-harness" / "prompts"
    ws_prompts.mkdir(parents=True)
    (ws_prompts / "coder.md").write_text("WORKSPACE LEVEL", encoding="utf-8")
    assert _role_prompt(cfg, "coder", "BUILTIN") == "WORKSPACE LEVEL"


def test_role_prompt_empty_files_skipped(tmp_path: Path):
    """An empty/placeholder file must not blank out lower-precedence layers."""
    cfg = _synthetic_config(tmp_path)
    prompts = tmp_path / "config" / "prompts"
    prompts.mkdir(parents=True)
    (prompts / "coder.md").write_text("CONFIG LEVEL", encoding="utf-8")
    ws_prompts = tmp_path / ".eco-harness" / "prompts"
    ws_prompts.mkdir(parents=True)
    (ws_prompts / "coder.md").write_text("   \n", encoding="utf-8")
    assert _role_prompt(cfg, "coder", "BUILTIN") == "CONFIG LEVEL"


@pytest.mark.parametrize("role,marker", [
    ("coder", "STEP 1"),
    ("coder", "to_tester"),
    ("tester", "run_artifact"),
    ("tester", "MUST NOT claim a criterion"),
])
def test_make_role_agent_uses_full_config_prompts(role: str, marker: str, tmp_path: Path):
    """Integration over the real repo config: the runtime system prompt must
    contain the full workflow content, not the old placeholder sentences."""
    cfg = load_config()
    model = Model(
        id="scripted", name="scripted", api="faux-scripted",
        provider="scripted", baseUrl="", cost=ModelCost(),
    )
    project_dir = tmp_path / f"proj-{role}"
    project_dir.mkdir()
    agent = make_role_agent(
        role,
        config=cfg,
        model=model,
        cli_path=None,
        project_dir=project_dir,
        make_exe=Path("make"),
        language="C",
        marketplace_cache_root=cfg.root / "marketplace_cache",
        mode="auto",
    )
    assert marker in agent.system_prompt
    assert "current coder role instructions" not in agent.system_prompt
    assert "current tester role instructions" not in agent.system_prompt


# ── 3. Host-mode artifact path resolution ────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_paths_warnings(monkeypatch):
    monkeypatch.setattr(tool_paths, "_warned", set())


@pytest.fixture
def isolated_env(monkeypatch, tmp_path):
    """No env vars, container root redirected into tmp_path."""
    monkeypatch.delenv("MARKETPLACE_CACHE_ROOT", raising=False)
    monkeypatch.delenv("MARKETPLACE_INDEX_PATH", raising=False)
    monkeypatch.setattr(tool_paths, "_CONTAINER_ROOT", tmp_path / "app")
    return tmp_path


def test_paths_env_overrides_everything(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKETPLACE_CACHE_ROOT", str(tmp_path / "custom-cache"))
    monkeypatch.setenv("MARKETPLACE_INDEX_PATH", str(tmp_path / "custom.sqlite"))
    assert tool_paths.marketplace_cache_root() == Path(tmp_path / "custom-cache")
    assert tool_paths.marketplace_index_path() == Path(tmp_path / "custom.sqlite")


def test_paths_repo_candidate_preferred(isolated_env):
    repo = isolated_env / "repo"
    (repo / "marketplace_cache").mkdir(parents=True)
    (repo / "marketplace_index.sqlite").touch()
    assert tool_paths.marketplace_cache_root(repo=repo) == (repo / "marketplace_cache").resolve()
    assert tool_paths.marketplace_index_path(repo=repo) == (repo / "marketplace_index.sqlite").resolve()


def test_paths_container_fallback(isolated_env):
    repo = isolated_env / "repo"
    repo.mkdir()
    app_cache = isolated_env / "app" / "marketplace_cache"
    app_cache.mkdir(parents=True)
    assert tool_paths.marketplace_cache_root(repo=repo) == app_cache.resolve()


def test_paths_deterministic_when_missing(isolated_env):
    repo = isolated_env / "repo"
    repo.mkdir()
    expected = (repo / "marketplace_cache").resolve()
    assert tool_paths.marketplace_cache_root(repo=repo) == expected
