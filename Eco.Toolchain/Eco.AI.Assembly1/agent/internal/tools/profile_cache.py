"""``read_component_profile`` — quick (cid, version, fileId) lookup.

Why this exists
---------------
The architect agent's flow is:

  1. search_marketplace(query)        → component NAME
  2. ??? get (cid, version, fileId)   ← this tool
  3. eco_cli(['pull', cid, ver, fid]) → download DEVKIT

Step 2 needs CID + version + DEVKIT fileId. Three ways to get them:

  (a) eco_cli(['find','-c','<CID>']) — but you need CID first, and the
      only way to get CID from a name is eco_cli(['find','-p']) catalog
      dump — slow (full marketplace listing) and defeats the point of
      having RAG do discovery.
  (b) Read it from marketplace_cache/_profiles/<Name>.json — a snapshot
      of (a) for all 30 published components, pre-fetched at build time
      by scripts/fetch_marketplace.py. Fast, no subprocess, no wine.
  (c) Add a CID column to the RAG index — cleanest but a bigger change
      (requires re-indexing, schema migration).

This tool implements (b): a thin read over the cached profile JSON. The
cache snapshot is on a :ro volume in production (docker-compose.yml ~ line
27) at /app/marketplace_cache. read_file inside the architect is
sandboxed to project_dir (tools/io.py:ensure_inside) so it cannot reach
the cache directly — hence this dedicated tool with a fixed-root resolve.

If the profile is missing (cache stale or component added since the
snapshot), the tool returns is_error=True with a message that points the
agent at the eco_cli fallback path.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from agent.internal.eco_agent import EcoTool, ToolResult


# Match the production volume mount in docker-compose.yml (./marketplace_cache
# → /app/marketplace_cache:ro). Override via env for tests / dev hosts.
_DEFAULT_CACHE_ROOT = Path(os.environ.get(
    "MARKETPLACE_CACHE_ROOT",
    "/app/marketplace_cache",
))


_RE_IID = re.compile(r"(IID_[A-Za-z0-9_]+)\s*(?:=)")
_RE_FACTORY = re.compile(r"GetIEcoComponentFactoryPtr_[A-Fa-f0-9]{32}")
_RE_VMETHOD = re.compile(r"ECOCALLMETHOD\s+\*?\s*([A-Za-z_][A-Za-z0-9_]*)")


def _scan_sharedfiles(cache_root: Path, name: str, cid: str) -> str:
    """Build a compact CONTRACT CARD from a component's SharedFiles.

    Returns IIDs, the static factory symbol, the vtable method names of every
    ``IEco*.h`` interface, and the header layout. This lets the architect get
    the exact contract without raw-reading 12 KB Cyrillic-heavy headers (which
    the context builder would later elide).
    """
    sf = cache_root / name / "SharedFiles"
    if not sf.is_dir():
        return ""

    headers = sorted(p.name for p in sf.glob("*.h"))
    iids: list[str] = []
    factory: Optional[str] = None
    vmethods: dict[str, list[str]] = {}
    seen_methods: set[str] = set()

    for h in sorted(sf.glob("*.h")):
        try:
            text = h.read_text(encoding="utf-8-sig", errors="replace")
        except OSError:
            continue
        for m in _RE_IID.finditer(text):
            if m.group(1) not in iids:
                iids.append(m.group(1))
        fm = _RE_FACTORY.search(text)
        if fm and factory is None:
            factory = fm.group(0)
        if h.name.startswith("IEco") and h.name.endswith(".h"):
            for vm in _RE_VMETHOD.finditer(text):
                meth = vm.group(1)
                if meth in ("ECOCALLMETHOD",):
                    continue
                if meth not in seen_methods:
                    seen_methods.add(meth)
                    vmethods.setdefault(h.name, []).append(meth)

    lines = ["", "### Contract card (from SharedFiles/)", ""]
    lines.append(f"- **factory**: `{factory or ('GetIEcoComponentFactoryPtr_' + cid)}`")
    if iids:
        lines.append(f"- **IIDs**: {', '.join('`' + i + '`' for i in iids)}")
    lines.append(f"- **SharedFiles layout**: {', '.join(headers)}")
    for hname, methods in vmethods.items():
        capped = methods[:40]
        lines.append(f"- **{hname} vtable**: {', '.join(capped)}"
                     + (" …" if len(methods) > 40 else ""))
    return "\n".join(lines)


class _ProfileArgs(BaseModel):
    """Arguments for ``read_component_profile``.

    The description below is what the LLM sees in its tool schema —
    keep it self-contained.
    """
    name: str = Field(
        ...,
        description=(
            "Component base name without _DK_v.* suffix, e.g. "
            "'Eco.Math.C89'. Match the ``component`` field returned by "
            "search_marketplace exactly."
        ),
    )


def _read_profile(args: _ProfileArgs, cache_root: Path) -> ToolResult:
    profile_path = cache_root / "_profiles" / f"{args.name}.json"
    if not profile_path.exists():
        # List what IS in the cache so the agent can spot a typo without
        # falling all the way back to the eco_cli catalog dump.
        profiles_dir = cache_root / "_profiles"
        available: list[str] = []
        if profiles_dir.is_dir():
            available = sorted(p.stem for p in profiles_dir.glob("*.json"))
        hint = ""
        if available:
            hint = (
                f"\nCache has profiles for: {', '.join(available)}.\n"
                f"If the name is correct but missing here, fall back to "
                f"eco_cli(['find','-p']) once to discover the cid, then "
                f"eco_cli(['find','-c', cid]) for live metadata."
            )
        return ToolResult(
            content=(
                f"read_component_profile: no cached profile for "
                f"{args.name!r} at {profile_path}.{hint}"
            ),
            is_error=True,
            details={"name": args.name, "expected_path": str(profile_path)},
        )

    # Profiles were written by scripts/fetch_marketplace.py with a UTF-8
    # BOM — open via utf-8-sig so the BOM is stripped before parse.
    try:
        with profile_path.open(encoding="utf-8-sig") as f:
            profile = json.load(f)
    except json.JSONDecodeError as e:
        return ToolResult(
            content=(
                f"read_component_profile: profile at {profile_path} is "
                f"not valid JSON: {e}"
            ),
            is_error=True,
            details={"name": args.name, "path": str(profile_path)},
        )

    cid = profile.get("cid")
    versions = profile.get("versions") or []
    if not cid or not versions:
        return ToolResult(
            content=(
                f"read_component_profile: profile at {profile_path} has "
                f"no cid or no versions[]. Raw keys: {list(profile.keys())}"
            ),
            is_error=True,
            details={"name": args.name, "cid": cid},
        )

    # Pick the latest published version. Convention: versions[-1] is the
    # newest (this is how eco_cli also orders them — see architect.py
    # taxonomy block).
    latest = versions[-1]
    version_name = latest.get("name", "")
    files = latest.get("files") or []
    devkit_entries = [f for f in files if f.get("contentType") == "DEVKIT"]
    if not devkit_entries:
        return ToolResult(
            content=(
                f"read_component_profile: latest version of {args.name} "
                f"has no DEVKIT file entry. Available contentTypes: "
                f"{sorted({f.get('contentType') for f in files})}"
            ),
            is_error=True,
            details={"name": args.name, "version": version_name},
        )
    devkit_file_id = devkit_entries[0].get("fileId")

    # Markdown body so the model can parrot the values back verbatim into
    # its next eco_cli pull call. Details mirror the body as a structured
    # dict for any downstream consumer.
    card = _scan_sharedfiles(resolved_root, args.name, cid)
    body_lines = [
        f"## Component profile: {args.name}",
        "",
        f"- **cid**: `{cid}`",
        f"- **version**: `{version_name}`",
        f"- **devkit_file_id**: `{devkit_file_id}`",
        "",
        "Next step: eco_cli(['pull','-c','" + cid + "',"
        "'-v','" + version_name + "','-fid=" + str(devkit_file_id) + "']).",
    ]
    if card:
        body_lines.append(card)
    return ToolResult(
        content="\n".join(body_lines),
        details={
            "name": args.name,
            "cid": cid,
            "version": version_name,
            "devkit_file_id": devkit_file_id,
        },
    )


def make_read_component_profile_tool(
    *,
    cache_root: Optional[Path] = None,
) -> EcoTool:
    """Build the ``read_component_profile`` EcoTool.

    Args:
        cache_root: Override for the marketplace cache root directory.
                    ``None`` uses ``MARKETPLACE_CACHE_ROOT`` env or the
                    production default (/app/marketplace_cache).

    Returns:
        EcoTool with name ``read_component_profile``.
    """
    resolved_root = Path(cache_root) if cache_root else _DEFAULT_CACHE_ROOT
    return EcoTool(
        name="read_component_profile",
        description=(
            "Look up (cid, version, devkit_file_id) for a marketplace "
            "component name. Reads the local cached profile snapshot at "
            "marketplace_cache/_profiles/<Name>.json — much faster than "
            "round-tripping through eco_cli find -p + find -c. Use this "
            "AFTER search_marketplace identified a component name, and "
            "BEFORE eco_cli pull."
        ),
        args_schema=_ProfileArgs,
        execute=lambda a: _read_profile(a, resolved_root),
    )

