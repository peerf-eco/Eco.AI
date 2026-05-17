"""Browser-relay proxy stub.

Per docs/superpowers/specs/2026-05-18-pi-port-design.md (Out of scope), the
browser proxy is intentionally not implemented in Phase 2. This module is a
placeholder so callers attempting to import it get a clear error rather than
ModuleNotFoundError.
"""
from __future__ import annotations


def make_proxy(*args, **kwargs):
    """Not implemented. See docs/superpowers/specs/2026-05-18-pi-port-design.md."""
    raise NotImplementedError(
        "pi_agent_core.proxy is a stub. Web-UI proxy is out of scope for Phase 2."
    )
