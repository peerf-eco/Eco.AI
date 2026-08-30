"""Stable hashing for cache hints and session IDs."""
from __future__ import annotations

import hashlib
import json
from typing import Any


def sha256_hex(data: Any) -> str:
    """Hash any JSON-serializable value as hex sha256."""
    if isinstance(data, (str, bytes)):
        raw = data.encode("utf-8") if isinstance(data, str) else data
    else:
        raw = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
