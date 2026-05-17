"""Partial-JSON accumulator for streaming tool_call.arguments deltas.

Tool-call argument strings are streamed character-by-character in OpenAI-compat
delta chunks. We accumulate the raw string and attempt to parse it at each step.
The result is "best-effort partial dict" - if the JSON is incomplete, we use
`partial_json_parser` to coerce. On final completion we use stdlib json.loads
for strict validation.

This replaces TypeScript's `partial-json` package (utils/json-parse.ts).
"""
from __future__ import annotations

import json
from typing import Any

try:
    from partial_json_parser import loads as _partial_loads
    _HAS_PARTIAL = True
except ImportError:
    _HAS_PARTIAL = False


def parse_partial(raw: str) -> Any:
    """Parse a (possibly incomplete) JSON string. Returns a dict if at all
    parseable, else {}."""
    if not raw or not raw.strip():
        return {}
    # Try strict parse first - fastest when the chunk is complete
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    # Partial path
    if _HAS_PARTIAL:
        try:
            return _partial_loads(raw)
        except Exception:
            pass
    # Fallback: nothing parseable yet
    return {}


def parse_strict(raw: str) -> Any:
    """Parse a complete JSON string, raising ValueError on any failure."""
    try:
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e
