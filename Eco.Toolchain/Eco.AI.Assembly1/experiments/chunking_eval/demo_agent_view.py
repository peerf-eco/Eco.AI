#!/usr/bin/env python3
"""Demo: format retrieval results EXACTLY as the agent will see them.

This is the contract preview for ``search_marketplace`` EcoTool — same
markdown ``content`` and same structured ``details`` dict that will hit
the agent. No agent yet; we just run the HybridRetriever against the
production-stack AST index and format the output.

Run:
    python experiments/chunking_eval/demo_agent_view.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

from agent.rag.embedder import Embedder
from agent.rag.retrieve import HybridRetriever, RetrievalResult
from agent.rag.store import RagStore


def format_result_markdown(query: str, results: list[RetrievalResult], k: int = 5) -> str:
    """The string the LLM agent will receive in tool's ``ToolResult.content``.

    Conventions:
        - Header line names the query — easy to spot in long traces.
        - Each hit gets a [N] number for the LLM to reference back.
        - ``component/file:lines`` first, then ``kind=X name=Y score=Z`` — agent
          can pattern-match either of these.
        - Snippet is a fenced ``c`` block, capped at ~400 chars to keep
          tool output small in the agent's context.
    """
    lines = [
        f"=== search_marketplace: {len(results)} results for {query!r} (showing top {k}) ===",
        "",
    ]
    for i, r in enumerate(results[:k], 1):
        snippet = r.text.strip()
        if len(snippet) > 400:
            snippet = snippet[:400] + "\n...(truncated)"
        lines.append(f"[{i}] {r.location()}")
        lines.append(
            f"    kind={r.kind} name={r.name or '-'} score={r.score:.4f}"
        )
        lines.append("    ```c")
        for snippet_line in snippet.splitlines():
            lines.append(f"    {snippet_line}")
        lines.append("    ```")
        lines.append("")
    return "\n".join(lines)


def format_result_details(query: str, results: list[RetrievalResult], k: int = 5) -> dict:
    """The dict the LLM does NOT see, but tests / metrics do.

    Same data as the markdown, but structured. Used by:
      - integration tests (assert specific component/file in top-k)
      - eval / golden-query scoring
      - downstream tools that want machine-readable hits
    """
    return {
        "query": query,
        "results": [
            {
                "rank": i + 1,
                "rowid": r.rowid,
                "component": r.component,
                "file": r.file,
                "kind": r.kind,
                "name": r.name,
                "lines": f"L{r.line_start}-L{r.line_end}",
                "score": round(r.score, 4),
                "snippet_chars": len(r.text),
            }
            for i, r in enumerate(results[:k])
        ],
        "total_candidates": len(results),
    }


def main() -> int:
    index = PROJECT_ROOT / "experiments" / "chunking_eval" / "artifacts" / "ast.sqlite"
    if not index.exists():
        sys.exit(f"index not found: {index} — run run_eval.py first")

    embedder = Embedder()
    # Probe dim
    embedder.embed_one("dim probe")
    store = RagStore(index, embed_dim=embedder.dim)
    retr = HybridRetriever(store, embedder)

    demo_queries = [
        ("semantic", "component for calculating power and square root of a number", None),
        ("exact_name", "IEcoComponentFactory interface vtable with QueryInterface and Alloc", None),
        ("error_code", "ERR_ECO_NOBUS meaning", "macro"),
        ("type_layout", "UGUID struct fields Preamble Length Data", None),
        ("kind_filter", "list iterator methods", "interface"),
    ]

    for category, query, kind in demo_queries:
        print("=" * 78)
        print(f"category: {category}    kind_filter: {kind or '(any)'}")
        print("=" * 78)
        print(f"INPUT  args: query={query!r}, k=5, kind={kind!r}, component=None")
        print()
        results = retr.search(query, k=5, kind=kind)
        print("--- ToolResult.content (what the agent SEES, markdown) ---")
        print(format_result_markdown(query, results))
        print("--- ToolResult.details (structured, NOT shown to LLM) ---")
        details = format_result_details(query, results)
        print(json.dumps(details, indent=2, ensure_ascii=False)[:2000])
        print()

    store.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
