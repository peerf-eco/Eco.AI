"""Pure-Python regex parsers for inter-node Markdown handoffs (V5)."""

import re
from typing import Any


_PROJECT_RE = re.compile(r"^##\s*Project:\s*(?P<name>.+?)\s*$", re.MULTILINE)
_BULLET_RE = re.compile(
    r"^-\s+\*\*(?P<name>[^*]+?)\*\*\s*[—\-]\s*"
    r"source:\s*(?P<source>sdk|marketplace|develop)"
    r"(?:\s*[—\-]\s*(?P<reason>.+?))?$",
    re.MULTILINE,
)
_SPEC_RE = re.compile(r"^\s+-\s*spec:\s*(?P<spec>.+?)$", re.MULTILINE)
_PLATFORM_RE = re.compile(r"^-\s*Platform:\s*(?P<platform>\S+)\s*$", re.MULTILINE)
_OUTPUT_RE = re.compile(r"^-\s*Output:\s*(?P<output>\S+)\s*$", re.MULTILINE)


def parse_plan(plan_md: str) -> dict[str, Any]:
    """Extract structured plan from Markdown PRD.

    Returns dict with keys: project_name, components (list), platform, output.
    On unparseable input, returns empty/default values rather than raising.
    """
    project_match = _PROJECT_RE.search(plan_md)
    project_name = project_match["name"].strip() if project_match else ""

    components: list[dict[str, Any]] = []
    for m in _BULLET_RE.finditer(plan_md):
        components.append({
            "name": m["name"].strip(),
            "source": m["source"],
            "reason": (m["reason"] or "").strip(),
            "spec": None,
        })

    # Attach spec to immediately-preceding develop bullet (if line below is "  - spec: ...")
    bullet_positions = [(m.start(), m.end()) for m in _BULLET_RE.finditer(plan_md)]
    spec_matches = list(_SPEC_RE.finditer(plan_md))
    for i, (b_start, b_end) in enumerate(bullet_positions):
        next_bullet_start = bullet_positions[i + 1][0] if i + 1 < len(bullet_positions) else len(plan_md)
        for sm in spec_matches:
            if b_end < sm.start() < next_bullet_start:
                components[i]["spec"] = sm["spec"].strip()
                break

    platform_match = _PLATFORM_RE.search(plan_md)
    platform = platform_match["platform"] if platform_match else ""
    output_match = _OUTPUT_RE.search(plan_md)
    output = output_match["output"] if output_match else ""

    return {
        "project_name": project_name,
        "components": components,
        "platform": platform,
        "output": output,
    }
