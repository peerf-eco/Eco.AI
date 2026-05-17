"""Server-Sent Events (SSE) parser for httpx async streams.

OpenAI-compat providers send chunks as `data: <json>\\n\\n` lines. We split
on blank lines, parse each `data:` payload as JSON, and yield dicts. The
special sentinel `data: [DONE]` terminates the stream (we yield nothing for it).
"""
from __future__ import annotations

import json
from typing import AsyncIterator

import httpx


async def parse_sse(response: httpx.Response) -> AsyncIterator[dict]:
    """Yield parsed JSON dicts from an httpx streaming response.

    Errors:
    - Lines that don't start with `data: ` are skipped (typically SSE comments).
    - JSON decode errors are skipped silently (some providers send keep-alive
      pings as non-JSON; logging would be too noisy).
    """
    buffer = b""
    async for chunk in response.aiter_bytes():
        buffer += chunk
        while b"\n\n" in buffer:
            block, buffer = buffer.split(b"\n\n", 1)
            for line in block.split(b"\n"):
                line = line.strip()
                if not line.startswith(b"data:"):
                    continue
                payload = line[5:].strip()  # strip "data:" prefix
                if payload == b"[DONE]":
                    return
                if not payload:
                    continue
                try:
                    yield json.loads(payload)
                except json.JSONDecodeError:
                    continue
