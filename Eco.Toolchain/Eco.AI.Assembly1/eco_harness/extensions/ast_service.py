from __future__ import annotations

from pathlib import Path
from typing import Any


class AstService:
    def parse(self, path: Path) -> dict[str, Any]:
        if not path.is_file():
            raise FileNotFoundError(path)
        from agent.rag.chunker_ast import ASTChunker

        text = path.read_text(encoding="utf-8", errors="replace")
        chunks = ASTChunker(target_chars=400).chunk(text, path.name)
        return {
            "path": path.as_posix(),
            "symbols": [
                {
                    "name": chunk.name,
                    "kind": chunk.kind.value,
                    "line_start": chunk.line_start,
                    "line_end": chunk.line_end,
                }
                for chunk in chunks
                if chunk.name
            ],
            "interfaces": [
                chunk.name
                for chunk in chunks
                if chunk.kind.value == "interface" and chunk.name
            ],
            "vtables": [
                chunk.name
                for chunk in chunks
                if chunk.kind.value == "interface" and "VTbl" in chunk.text
            ],
        }