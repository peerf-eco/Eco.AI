from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from agent.domain import load_acom_domain, load_tool_contract


_SOURCE_EXTENSIONS = frozenset(
    {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx", ".idl", ".inc"},
)


def _iter_source_files(roots: Iterable[Path]) -> list[Path]:
    paths: set[Path] = set()
    for root in roots:
        root = Path(root)
        if root.is_file() and root.suffix.lower() in _SOURCE_EXTENSIONS:
            paths.add(root.resolve())
            continue
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in _SOURCE_EXTENSIONS:
                paths.add(path.resolve())
    return sorted(paths, key=lambda path: path.as_posix().lower())


def stitch_source_files(
    roots: Iterable[Path],
    *,
    max_bytes: int = 300_000,
) -> str:
    sections: list[str] = []
    used = 0
    for path in _iter_source_files(roots):
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


def _core1_sharedfiles(roots: Iterable[Path]) -> Path | None:
    """Locate ``Eco.Core1/SharedFiles`` within the given source roots.

    Eco.Core1 is the constant ACOM base (core types, ``IEcoUnknown``,
    ``IEcoBase1``, ``IEcoComponentFactory``, ``IEcoSystem1``, ``ErrEcoCodes``).
    Stitching it into the static prompt tail makes it a stable prefix, which
    maximizes provider KV-cache reuse across turns and across C tasks — far
    cheaper than the old full-marketplace stitch that blew the context window.
    """
    for root in roots:
        candidate = Path(root) / "Eco.Core1" / "SharedFiles"
        if candidate.is_dir():
            return candidate.resolve()
        resolved = Path.cwd() / root / "Eco.Core1" / "SharedFiles"
        if resolved.is_dir():
            return resolved.resolve()
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
            str(Path(__file__).resolve().parents[2] / "config" / "prompts" / "acom_system_header.md"),
        ),
    )
    header = header_file.read_text(encoding="utf-8") if header_file.exists() else ""
    # Curated, constant base: stitch Eco.Core1/SharedFiles into the static
    # prompt tail. This is the always-needed ACOM foundation (core types,
    # interfaces, error codes, macros) — a stable prefix that maximizes
    # provider KV-cache hits. Unlike the old full-marketplace stitch (which
    # blew the window), this is small and does not change per turn.
    core1 = _core1_sharedfiles(source_roots)
    source = ""
    if core1 is not None:
        source = stitch_source_files([core1], max_bytes=min(max_source_bytes, 120_000))
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