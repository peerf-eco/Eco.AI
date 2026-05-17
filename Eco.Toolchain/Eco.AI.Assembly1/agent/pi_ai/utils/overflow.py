"""Helpers for detecting/anticipating context-window overflow.

Trivial port - we only ship the rough char->token estimator. Real token counting
is provider-specific and lives in pi_agent_core's transformContext hook.
"""
from __future__ import annotations


def estimate_tokens_from_chars(num_chars: int) -> int:
    """Rough heuristic: ~4 chars per token for English-heavy content.
    Conservative for code (which has more tokens per char) but adequate
    for first-pass overflow detection. Real tokenization belongs in
    pi_agent_core/transformContext hook with tiktoken."""
    return num_chars // 4


def would_overflow(
    estimated_input_tokens: int,
    *,
    context_window: int,
    safety_margin: int = 1024,
) -> bool:
    """Returns True if estimated input is unsafely close to context_window."""
    return estimated_input_tokens + safety_margin >= context_window
