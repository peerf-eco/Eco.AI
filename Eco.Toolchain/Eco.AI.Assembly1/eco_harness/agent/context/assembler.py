from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from eco_harness.agent.domain import load_acom_domain, load_tool_contract
from eco_harness.agent.internal.tools.paths import (
    PACKAGE_ROOT,
    framework_root,
    repo_root,
)


_SOURCE_EXTENSIONS = frozenset(
    {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".idl", ".inc"},
)

# The curated Eco.Core1 stitch is C-only: the ACOM base headers ship as C
# headers (.h) plus their C++ wrappers (.hpp). Agents author C89, and the
# .hpp duplicates add ~30% tokens to a byte-identical prompt block.
_CORE1_STITCH_EXTENSIONS = frozenset({".h"})


def _iter_source_files(
    roots: Iterable[Path],
    *,
    extensions: frozenset[str] | None = None,
) -> list[Path]:
    allowed = extensions or _SOURCE_EXTENSIONS
    paths: set[Path] = set()
    for root in roots:
        root = Path(root)
        if root.is_file() and root.suffix.lower() in allowed:
            paths.add(root.resolve())
            continue
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in allowed:
                paths.add(path.resolve())
    return sorted(paths, key=lambda path: path.as_posix().lower())


def stitch_source_files(
    roots: Iterable[Path],
    *,
    max_bytes: int = 300_000,
    extensions: frozenset[str] | None = None,
) -> str:
    sections: list[str] = []
    used = 0
    for path in _iter_source_files(roots, extensions=extensions):
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        section = (
            f"// --- START_FILE: {path.as_posix()} ---\n"
            f"{content.rstrip()}\n"
            f"// --- END_FILE: {path.as_posix()} ---\n"
        )
        encoded_size = len(section.encode("utf-8"))
        if used + encoded_size > max_bytes:
            remaining = max_bytes - used
            if remaining > 256:
                clipped = section.encode("utf-8")[:remaining].decode(
                    "utf-8",
                    errors="ignore",
                )
                sections.append(clipped + "\n// --- FILE_TRUNCATED: context limit reached ---\n")
            break
        sections.append(section)
        used += encoded_size
    return "".join(sections) or "(no C/C++ source files available)"


def _core1_candidates(root: Path) -> list[Path]:
    """Eco.Core1/SharedFiles locations under one root.

    Handles both layouts:

      - flat:        ``<root>/Eco.Core1/SharedFiles``
      - versioned DK ``<root>/Eco.Core1_DK_v.<ver>/Eco.Core1/SharedFiles``

    The versioned layout is what the ACOM marketplace ships and what
    ``eco-cli pull -d $ECO_FRAMEWORK`` deposits, so it is discovered
    automatically (highest version number wins if several are present).
    """
    root = Path(root)
    flat = root / "Eco.Core1" / "SharedFiles"
    if flat.is_dir():
        return [flat.resolve()]
    nested: list[Path] = []
    for dk in sorted(root.glob("Eco.Core1_DK_v.*"), reverse=True):
        candidate = dk / "Eco.Core1" / "SharedFiles"
        if candidate.is_dir():
            nested.append(candidate.resolve())
    return nested


def _core1_sharedfiles(roots: Iterable[Path]) -> Path | None:
    """Locate ``Eco.Core1/SharedFiles`` across the given roots + ECO_FRAMEWORK.

    Eco.Core1 is the constant ACOM base (core types, ``IEcoUnknown``,
    ``IEcoBase1``, ``IEcoComponentFactory``, ``IEcoSystem1``, ``ErrEcoCodes``).
    Stitching it into the static prompt tail makes it a stable prefix, which
    maximizes provider KV-cache reuse across turns and across C tasks — far
    cheaper than the old full-marketplace stitch that blew the context window.

    The standard ACOM ``ECO_FRAMEWORK`` environment variable is consulted
    first (it points at the development-kit tree on host machines), then the
    configured source roots (``harness.yaml:source_roots``, typically the
    in-repo ``eco_framework/`` checkout and ``marketplace_cache``).
    """
    candidates_roots: list[Path] = [framework_root()]
    candidates_roots.extend(Path(root) for root in roots)
    for root in candidates_roots:
        for candidate in _core1_candidates(root):
            return candidate
    return None


def build_static_system_prompt(
    role_prompt: str,
    *,
    source_roots: Iterable[Path],
    tool_contract: str = "",
    domain_knowledge: str = "",
    header_path: Path | None = None,
    max_source_bytes: int = 300_000,
) -> str:
    header_file = header_path or Path(
        os.getenv(
            "HARNESS_SYSTEM_HEADER",
            str(repo_root() / "config" / "prompts" / "acom_system_header.md"),
        ),
    )
    if not header_file.exists():
        packaged = PACKAGE_ROOT / "config" / "prompts" / "acom_system_header.md"
        if packaged.exists():
            header_file = packaged
    header = header_file.read_text(encoding="utf-8") if header_file.exists() else ""
    # Curated, constant base: stitch Eco.Core1/SharedFiles into the static
    # prompt tail. This is the always-needed ACOM foundation (core types,
    # interfaces, error codes, macros) — a stable prefix that maximizes
    # provider KV-cache hits. Unlike the old full-marketplace stitch (which
    # blew the window), this is small and does not change per turn.
    core1 = _core1_sharedfiles(source_roots)
    source = ""
    if core1 is not None:
        # C-only stitch (.h): the .hpp C++ wrappers duplicate the same
        # declarations and would burn ~30% more tokens on a block that is
        # byte-identical across every call (KV-cache prefix).
        source = stitch_source_files(
            [core1],
            max_bytes=min(max_source_bytes, 120_000),
            extensions=_CORE1_STITCH_EXTENSIONS,
        )
    domain = domain_knowledge or load_acom_domain()
    stable_tools = tool_contract or load_tool_contract()
    return (
        f"{header.rstrip()}\n\n"
        f"=== STATIC ACOM DOMAIN KNOWLEDGE ===\n{domain.rstrip()}\n\n"
        f"=== STATIC TOOL CONTRACT ===\n{stable_tools.rstrip()}\n\n"
        f"=== ROLE INSTRUCTIONS ===\n{role_prompt.rstrip()}\n\n"
        f"=== IMMUTABLE SOURCE CODEBASE (curated Eco.Core1 base) ===\n"
        f"{source or '(Eco.Core1 SharedFiles not found in source_roots)'}"
    )


def build_dynamic_tail(
    *,
    rag_context: str = "",
    tool_logs: Iterable[str] = (),
    user_prompt: str = "",
    max_tool_logs: int = 5,
) -> str:
    logs = list(tool_logs)[-max_tool_logs:]
    sections = ["=== DYNAMIC CONTEXT TAIL ==="]
    if rag_context:
        sections.extend(["=== RAG DOCUMENTATION ===", rag_context])
    if logs:
        sections.extend(["=== RECENT TOOL OUTPUTS ===", "\n\n".join(logs)])
    if user_prompt:
        sections.extend(["=== CURRENT USER REQUEST ===", user_prompt])
    return "\n".join(sections)