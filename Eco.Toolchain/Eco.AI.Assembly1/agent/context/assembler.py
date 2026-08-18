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
    # NOTE: The full marketplace cache used to be stitched into every system
    # prompt here (~80k tokens of component headers). That blew the context
    # window and is redundant — agents discover components on demand via the
    # sqlite-vec RAG index / search_marketplace tool instead. Static injection
    # is disabled for now; a curated, much shorter context (rules / AGENT.md)
    # will be wired in here later. Keep the plumbing (source_roots / max_bytes)
    # intact so it can be re-enabled or swapped.
    source = ""
    domain = domain_knowledge or load_acom_domain()
    stable_tools = tool_contract or load_tool_contract()
    return (
        f"{header.rstrip()}\n\n"
        f"=== STATIC ACOM DOMAIN KNOWLEDGE ===\n{domain.rstrip()}\n\n"
        f"=== STATIC TOOL CONTRACT ===\n{stable_tools.rstrip()}\n\n"
        f"=== ROLE INSTRUCTIONS ===\n{role_prompt.rstrip()}\n\n"
        f"=== IMMUTABLE SOURCE CODEBASE ===\n{source}"
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