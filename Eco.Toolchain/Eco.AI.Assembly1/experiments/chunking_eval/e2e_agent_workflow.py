#!/usr/bin/env python3
"""End-to-end agent workflow simulation.

What it does
------------
Pretends to be the V7 architect agent given a real diploma task:

    "Build a calculator component using pow and sqrt from EcoOS Math.C89.
     It must register on the InterfaceBus and use Core1 framework."

Walks through what the agent would actually do, calling our RAG and our
existing eco_cli tool just like the real EcoAgent would:

    1. Search marketplace for relevant components (3 queries × 5 results)
    2. Parse hits → derive set of components to pull
    3. Pull each component via eco-cli into a fresh project dir
    4. Verify project dir contains expected headers (IEcoBase1.h,
       IEcoMathC89.h, IEcoInterfaceBus1.h, etc.)

Output
------
Prints every step in markdown so a human reader sees exactly what the LLM
would see, then a final verification table showing whether the calculator
could compile (= all required headers present in project dir).

This is NOT the production EcoTool runtime — that's still TODO. This is a
"smoke test of the smoke test": prove end-to-end that the RAG outputs are
*actionable* for a downstream task.
"""
from __future__ import annotations

import os
import shutil
import subprocess
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
from agent.rag.retrieve import HybridRetriever
from agent.rag.store import RagStore

# Demo project — a fresh dir we pretend the agent owns.
DEMO_PROJECT = PROJECT_ROOT / "e2e_demo_project"
# Try to find eco-cli with Linux priority
ECO_CLI = None
for path in [
    os.environ.get("ECO_CLI_PATH"),
    str(PROJECT_ROOT.parent.parent / "eco-cli-linux" / "eco-cli"),  # Linux ELF (preferred)
    str(PROJECT_ROOT.parent.parent / "eco-cli-windows" / "eco-cli.exe"),  # Windows .exe (fallback)
    "eco-cli",  # System PATH
    "eco-cli.exe",  # System PATH Windows
]:
    if not path:
        continue
    candidate = Path(path)
    if candidate.exists():
        ECO_CLI = candidate
        break

if ECO_CLI is None:
    ECO_CLI = Path(str(PROJECT_ROOT.parent.parent / "eco-cli-windows" / "eco-cli.exe"))  # Default fallback
INDEX = PROJECT_ROOT / "experiments" / "chunking_eval" / "artifacts" / "ast.sqlite"


def print_step(n: int, title: str) -> None:
    print(f"\n{'='*72}")
    print(f"STEP {n}: {title}")
    print('='*72)


def search(retr: HybridRetriever, query: str, k: int = 5, **kw) -> list:
    """Run search and print markdown-style output exactly as the agent will see it."""
    print(f"\n>>> search_marketplace(query={query!r}, k={k}, kind={kw.get('kind')!r})")
    results = retr.search_vector_only(query, k=k, **kw)
    print(f"\n=== Top {len(results)} results ===\n")
    for i, r in enumerate(results, 1):
        snippet = r.text.strip()
        if len(snippet) > 250:
            snippet = snippet[:250] + " …(truncated)"
        # Single-line snippet for compact log
        snippet = snippet.replace("\n", " ⏎ ")
        print(f"[{i}] {r.component}/{r.file}:L{r.line_start}-L{r.line_end}")
        print(f"    kind={r.kind} name={r.name or '—'} score={r.score:.4f}")
        print(f"    snippet: {snippet[:180]}{'…' if len(snippet) > 180 else ''}")
    return results


def main() -> int:
    if not INDEX.exists():
        sys.exit(f"index not found: {INDEX}")
    if not ECO_CLI.exists():
        sys.exit(f"eco-cli not found: {ECO_CLI}")
    if not os.getenv("ECO_API_TOKEN"):
        sys.exit("ECO_API_TOKEN not set in env")

    embedder = Embedder()
    embedder.embed_one("dim probe")
    store = RagStore(INDEX, embed_dim=embedder.dim)
    retr = HybridRetriever(store, embedder)

    print_step(0, "Task given to agent")
    task = (
        "Build a calculator component using pow and sqrt from EcoOS Math.C89. "
        "It must register on the InterfaceBus and use Core1 framework."
    )
    print(f"\n{task}")

    # ── Step 1: search for math functions ────────────────────────────────
    print_step(1, "Agent searches for math operations")
    math_hits = search(
        retr, "component for mathematical pow sqrt functions"
    )

    # ── Step 2: search for bus registration ──────────────────────────────
    print_step(2, "Agent searches for component registration")
    bus_hits = search(
        retr, "register component on interface bus IEcoInterfaceBus1"
    )

    # ── Step 3: search for framework essentials ──────────────────────────
    print_step(3, "Agent searches for ACOM framework base")
    core_hits = search(
        retr,
        "IEcoComponentFactory QueryInterface vtable layout for ACOM",
    )

    # ── Step 4: agent reasons about which components to pull ─────────────
    print_step(4, "Agent derives component list from hits")
    components_needed = set()
    for hits in (math_hits, bus_hits, core_hits):
        for r in hits[:3]:  # consider top-3 from each query
            components_needed.add(r.component)
    print(f"\nComponents identified from RAG: {sorted(components_needed)}")
    # Mandatory framework deps the agent knows about (from CLAUDE.md memory).
    mandatory = {"Eco.Core1", "Eco.System1", "Eco.InterfaceBus1",
                 "Eco.MemoryManager1", "Eco.FileSystemManagement1"}
    final_list = sorted(components_needed | mandatory)
    print(f"+ mandatory framework deps     : {sorted(mandatory)}")
    print(f"= final pull list ({len(final_list)} components): {final_list}")

    # ── Step 5: pull each via eco-cli ─────────────────────────────────────
    print_step(5, "Agent calls eco_cli to pull each component")
    if DEMO_PROJECT.exists():
        print(f"(cleaning previous demo project at {DEMO_PROJECT})")
        shutil.rmtree(DEMO_PROJECT, ignore_errors=True)
    DEMO_PROJECT.mkdir(parents=True, exist_ok=True)

    pull_results: list[dict] = []

    # Aliases the marketplace maintains: pulling X actually lands as Y on disk.
    # The agent learns these by walking the catalog once; here hard-coded.
    _ALIASES = {"Eco.System1": "EcoOS.Unikernel"}

    import json
    import re as _re
    _ANSI = _re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

    def _resolve_via_cli(name: str) -> dict | None:
        """Live ``eco-cli find -p -n <name>`` parse — what the real agent
        will do via the eco_cli EcoTool. Returns the parsed profile, or
        None if not found / parse failed."""
        proc = subprocess.run(
            [str(ECO_CLI), "find", "-p", "-n", name],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode != 0:
            return None
        text = _ANSI.sub("", proc.stdout)
        start = text.find("{")
        if start < 0:
            return None
        try:
            return json.loads(text[start:])
        except Exception:
            return None

    for comp in final_list:
        # Resolve aliases first — pulling Eco.System1 means pulling EcoOS.Unikernel.
        lookup_name = _ALIASES.get(comp, comp)
        if lookup_name != comp:
            print(f"\n(alias: {comp} → look up {lookup_name})")

        profile = _resolve_via_cli(lookup_name)
        if profile is None:
            print(f"\n>>> eco-cli find -p -n {lookup_name}: NOT FOUND")
            pull_results.append({
                "component": comp, "status": "not_in_marketplace", "files": 0,
            })
            continue

        uguid = profile["uguid"]
        versions = sorted(profile["versions"], key=lambda v: v.get("date") or "")
        latest = versions[-1]
        devkit = next((f for f in latest["files"]
                       if f.get("contentType") == "DEVKIT"), None)
        if devkit is None:
            pull_results.append({
                "component": comp, "status": "no_devkit", "files": 0,
            })
            continue
        ver = latest["name"]
        fid = devkit["fileId"]

        print(f"\n>>> eco-cli find -p -n {lookup_name}  → uguid={uguid}, ver={ver}, fid={fid}")
        print(f">>> eco-cli pull -c {uguid} -v {ver} -fid={fid}")
        proc = subprocess.run(
            [str(ECO_CLI), "pull", "-c", uguid, "-v", ver, f"-fid={fid}"],
            cwd=DEMO_PROJECT, capture_output=True, text=True, timeout=60,
        )
        if proc.returncode != 0:
            print(f"    PULL FAILED rc={proc.returncode}: {proc.stderr[:200]}")
            pull_results.append({
                "component": comp, "status": "pull_failed",
                "uguid": uguid, "files": 0,
            })
            continue
        # Marketplace lands artefact under the profile's name, which may
        # differ from the alias the agent searched by.
        landed_name = profile.get("name", lookup_name)
        target = DEMO_PROJECT / landed_name
        files_pulled = len(list(target.rglob("*"))) if target.exists() else 0
        print(f"    OK → {target.name}/ ({files_pulled} entries)")
        pull_results.append({
            "component": comp, "status": "ok",
            "uguid": uguid, "version": ver, "files": files_pulled,
            "landed_as": landed_name,
        })

    # ── Step 6: verify the agent has what it needs ──────────────────────
    print_step(6, "Verification — does the project dir have what we need?")
    # Note: paths reflect REAL marketplace layout (verified 2026-05-24).
    # IEcoSystem1 interface declaration lives in Core1 (not in System1 —
    # System1 has *implementation*-side headers only: SystemInformation,
    # CommandArguments, etc.). Per-component CIDs live in ``ecoPackage.json``
    # at the project root after pull, so we don't need separate IdEcoSystem1.h.
    required_headers = {
        "Eco.Core1/SharedFiles/IEcoBase1.h": "ACOM base + UGUID + IEcoUnknown",
        "Eco.Core1/SharedFiles/IEcoSystem1.h": "framework system interface",
        "Eco.Core1/SharedFiles/ErrEcoCodes.h": "error code definitions",
        "Eco.InterfaceBus1/SharedFiles/IEcoInterfaceBus1.h": "bus registration API",
        "Eco.Math.C89/SharedFiles/IEcoMathC89.h": "pow / sqrt interface vtable",
        "Eco.Math.C89/SharedFiles/IdEcoMathC89.h": "math component CID literal",
        "ecoPackage.json": "marketplace metadata with all 6 CIDs",
    }
    print(f"\nChecking {len(required_headers)} required headers in {DEMO_PROJECT}:\n")
    all_ok = True
    for rel, why in required_headers.items():
        path = DEMO_PROJECT / rel
        ok = path.exists()
        status = "✅" if ok else "❌"
        if not ok:
            all_ok = False
        print(f"  {status}  {rel:60} — {why}")

    print()
    if all_ok:
        print("Result: ✅ ALL required headers are on disk. "
              "Coder can now compile a calculator that links against Math.C89, "
              "InterfaceBus1, System1, with the real ACOM ABI from Core1.")
    else:
        print("Result: ❌ Some required headers missing — see above.")

    print(f"\nPull summary ({sum(1 for p in pull_results if p['status']=='ok')} OK / "
          f"{len(pull_results)} total):")
    for p in pull_results:
        print(f"  {p['component']:30} {p['status']:20} files={p.get('files', 0)}")

    store.close()
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
