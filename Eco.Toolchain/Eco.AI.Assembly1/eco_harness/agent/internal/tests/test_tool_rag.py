"""Smoke tests for ``agent.internal.tools.rag.make_search_marketplace_tool``.

These don't hit OpenRouter — we monkey-patch ``Embedder.embed_one`` and
``RagStore`` so the test runs offline. The goal is to verify that the
EcoTool surface (args validation, ToolResult shape, markdown formatting,
``details`` payload) is what the EcoAgent loop expects.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from agent.internal.tools.rag import make_search_marketplace_tool


def _fake_result(rowid, component, file, kind, name, score, text):
    """Build a minimal duck-typed RetrievalResult.

    The real ``RetrievalResult`` is a dataclass; we don't import it here
    so the test stays decoupled from internals.
    """
    class _R:
        pass
    r = _R()
    r.rowid = rowid
    r.component = component
    r.file = file
    r.kind = kind
    r.name = name
    r.line_start = 10
    r.line_end = 20
    r.score = score
    r.text = text
    r.location = lambda: f"{component}/{file}:L10-L20"
    return r


class _FakeRetriever:
    def __init__(self):
        self.calls = []

    def search_vector_only(self, query, k, kind=None, component=None):
        self.calls.append({
            "query": query, "k": k, "kind": kind, "component": component,
        })
        # Return one or two fake results depending on query — enough to exercise
        # both the markdown formatter and the details payload.
        if "pow" in query.lower() or "sqrt" in query.lower():
            return [_fake_result(
                1, "Eco.Math.C89", "SharedFiles/IEcoMathC89.h",
                "interface", "IEcoMathC89VTbl", -0.42,
                "double (ECOCALLMETHOD *pow)(...);\ndouble (*sqrt)(...);",
            )]
        if "bus" in query.lower():
            return [
                _fake_result(
                    2, "Eco.InterfaceBus1", "SharedFiles/IEcoInterfaceBus1.h",
                    "interface", "IEcoInterfaceBus1VTbl", -0.55,
                    "RegisterComponent(...)",
                ),
                _fake_result(
                    3, "Eco.InterfaceBus1", "SharedFiles/IEcoInterfaceBus1.h",
                    "interface", "IEcoInterfaceBus1VTbl", -0.61,
                    "QueryComponent(...)",
                ),
            ]
        return []


@pytest.fixture
def patched_tool(monkeypatch, tmp_path):
    """Build the tool with internal init monkeypatched to return _FakeRetriever.

    Patch the imports the tool's ``_lazy_open`` closure performs locally:
    Embedder + RagStore + HybridRetriever. We replace HybridRetriever with
    the fake; the other two get throwaway stubs.
    """
    # Make ``index_path.exists()`` return True even though there's no real DB.
    fake_index = tmp_path / "fake.sqlite"
    fake_index.write_bytes(b"")  # 0-byte sentinel

    fake_retriever = _FakeRetriever()

    class _FakeEmbedder:
        def __init__(self, *a, **kw):
            self.model = "fake-model"
            self.dim = 4
        def embed_one(self, _t):
            return [0.0, 0.0, 0.0, 0.0]

    class _FakeStore:
        def __init__(self, *a, **kw):
            pass

    def _fake_hybrid(_store, _embedder):
        return fake_retriever

    monkeypatch.setattr("agent.rag.embedder.Embedder", _FakeEmbedder)
    monkeypatch.setattr("agent.rag.store.RagStore", _FakeStore)
    monkeypatch.setattr("agent.rag.retrieve.HybridRetriever", _fake_hybrid)

    tool = make_search_marketplace_tool(index_path=fake_index)
    return tool, fake_retriever


def test_tool_metadata(patched_tool):
    tool, _ = patched_tool
    assert tool.name == "search_marketplace"
    assert "marketplace" in tool.description.lower()
    # args_schema must be a pydantic BaseModel with the four documented fields
    schema = tool.args_schema.model_json_schema()
    assert "query" in schema["properties"]
    assert "k" in schema["properties"]
    assert "kind" in schema["properties"]
    assert "component" in schema["properties"]


def test_search_returns_markdown_with_hits(patched_tool):
    tool, retr = patched_tool
    args = tool.args_schema(query="component for pow and sqrt", k=3)
    result = tool.execute(args)
    assert result.is_error is False
    assert "Eco.Math.C89" in result.content
    assert "IEcoMathC89.h" in result.content
    assert "kind=interface" in result.content
    assert "name=IEcoMathC89VTbl" in result.content
    # details payload includes the structured fields used by tests / metrics
    details = result.details
    assert details["query"] == "component for pow and sqrt"
    assert details["result_count"] == 1
    assert details["results"][0]["component"] == "Eco.Math.C89"
    assert details["results"][0]["kind"] == "interface"
    # The mocked retriever should have been called once with our args
    assert retr.calls == [{
        "query": "component for pow and sqrt", "k": 3,
        "kind": None,  # 'any' → None into search_vector_only
        "component": None,
    }]


def test_kind_filter_translates_any_to_none(patched_tool):
    tool, retr = patched_tool
    args = tool.args_schema(
        query="register on bus", k=5, kind="interface",
    )
    tool.execute(args)
    assert retr.calls[-1]["kind"] == "interface"
    # And the 'any' default should send None
    args2 = tool.args_schema(query="register on bus", k=5)
    tool.execute(args2)
    assert retr.calls[-1]["kind"] is None


def test_empty_result_returns_helpful_message(patched_tool):
    tool, _ = patched_tool
    args = tool.args_schema(query="something completely unrelated", k=5)
    result = tool.execute(args)
    assert result.is_error is False
    assert "0 results" in result.content
    assert "widen the query" in result.content
    assert result.details["result_count"] == 0


def test_missing_index_returns_error(monkeypatch, tmp_path):
    # Build the tool pointing at a non-existent index — error should surface
    # only at execute time (lazy), not at factory time.
    tool = make_search_marketplace_tool(index_path=tmp_path / "nope.sqlite")
    args = tool.args_schema(query="x", k=1)
    result = tool.execute(args)
    assert result.is_error is True
    assert "not found" in result.content.lower()


def test_k_bounds_validated_by_pydantic(patched_tool):
    tool, _ = patched_tool
    with pytest.raises(Exception):  # pydantic ValidationError
        tool.args_schema(query="x", k=0)
    with pytest.raises(Exception):
        tool.args_schema(query="x", k=21)

