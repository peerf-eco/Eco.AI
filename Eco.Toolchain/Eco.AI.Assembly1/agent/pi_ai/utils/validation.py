"""Tool-argument validation against pydantic schemas.

In pi_agent_core, AgentTool defines parameters as a pydantic BaseModel subclass.
Before invoking execute(), we validate raw dict args against that schema. This
file provides a thin helper that returns (validated_obj, error_str_or_None).
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ValidationError


def validate_args(
    schema: type[BaseModel],
    raw_args: dict,
) -> tuple[Optional[BaseModel], Optional[str]]:
    """Validate raw dict against pydantic schema.

    Returns:
      (instance, None) on success
      (None, error_message) on failure
    """
    try:
        return schema.model_validate(raw_args), None
    except ValidationError as e:
        # Compact error message - provider sees this, must be model-friendly
        msgs = []
        for err in e.errors():
            loc = ".".join(str(p) for p in err["loc"])
            msgs.append(f"  - {loc}: {err['msg']}")
        return None, "Schema validation failed:\n" + "\n".join(msgs)
