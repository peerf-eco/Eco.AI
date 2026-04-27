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
_PLATFORM_RE = re.compile(r"^-\s*Platform:\s*(?P<platform>.+?)\s*$", re.MULTILINE)
_OUTPUT_RE = re.compile(r"^-\s*Output:\s*(?P<output>.+?)\s*$", re.MULTILINE)


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

    # Attach spec only to develop components (sdk/marketplace components don't have specs)
    bullet_positions = [(m.start(), m.end()) for m in _BULLET_RE.finditer(plan_md)]
    spec_matches = list(_SPEC_RE.finditer(plan_md))
    for i, (b_start, b_end) in enumerate(bullet_positions):
        if components[i]["source"] != "develop":
            continue
        next_bullet_start = bullet_positions[i + 1][0] if i + 1 < len(bullet_positions) else len(plan_md)
        for sm in spec_matches:
            if b_end < sm.start() < next_bullet_start:
                components[i]["spec"] = sm["spec"].strip()
                break

    platform_match = _PLATFORM_RE.search(plan_md)
    platform = platform_match["platform"].strip() if platform_match else ""
    output_match = _OUTPUT_RE.search(plan_md)
    output = output_match["output"].strip() if output_match else ""

    return {
        "project_name": project_name,
        "components": components,
        "platform": platform,
        "output": output,
    }


_STAGE_RE = re.compile(r"^##\s*Stage:\s*(?P<stage>\w+)\s*$", re.MULTILINE)
_STATUS_RE = re.compile(r"^##\s*Status:\s*(?P<status>\w+)\s*$", re.MULTILINE)
_ERROR_LINE_RE = re.compile(
    r"^-\s*(?P<file>[^:]+):(?P<line>\d+):\s*(?P<message>.+?)$",
    re.MULTILINE,
)
_TEST_FAIL_RE = re.compile(
    r"^-\s*(?P<test>\w+):\s*(?P<message>.+?)$",
    re.MULTILINE,
)


def parse_feedback(feedback_md: str) -> dict[str, Any]:
    """Extract structured failure info from Executor's back_to_code Markdown."""
    stage_match = _STAGE_RE.search(feedback_md)
    stage = stage_match["stage"] if stage_match else ""

    status_match = _STATUS_RE.search(feedback_md)
    status = status_match["status"] if status_match else ""

    errors_section = _section(feedback_md, "Errors")
    errors = [
        {"file": m["file"].strip(), "line": int(m["line"]), "message": m["message"].strip()}
        for m in _ERROR_LINE_RE.finditer(errors_section)
    ]

    tests_section = _section(feedback_md, "Test failures")
    test_failures = [
        {"test": m["test"], "message": m["message"].strip()}
        for m in _TEST_FAIL_RE.finditer(tests_section)
    ]

    return {
        "stage": stage,
        "status": status,
        "errors": errors,
        "test_failures": test_failures,
    }


def _section(md: str, heading: str) -> str:
    """Return everything between '## <heading>' and the next '## ' heading (or EOF)."""
    pattern = re.compile(rf"^##\s*{re.escape(heading)}\s*$", re.MULTILINE)
    m = pattern.search(md)
    if not m:
        return ""
    start = m.end()
    next_h = re.search(r"^##\s+", md[start:], re.MULTILINE)
    end = start + next_h.start() if next_h else len(md)
    return md[start:end]
