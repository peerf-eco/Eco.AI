from agent.parsers import parse_plan


SAMPLE_PRD = """\
## Project: Calc1

A simple calculator with logging.

## Components

- **Eco.Math.C89** — source: sdk — provides arithmetic primitives
- **Eco.StdIO.C89** — source: sdk — provides stdin/stdout
- **Eco.Logger1** — source: marketplace — structured logging
- **CalcController** — source: develop — glue logic
  - spec: methods Add(a,b), Subtract(a,b); depends on Math.C89

## Build target

- Platform: Windows
- Output: calc.exe

## Acceptance criteria

- Reads two numbers from stdin
- Prints sum to stdout
"""


def test_parse_plan_extracts_project_name():
    result = parse_plan(SAMPLE_PRD)
    assert result["project_name"] == "Calc1"


def test_parse_plan_extracts_all_components():
    result = parse_plan(SAMPLE_PRD)
    names = [c["name"] for c in result["components"]]
    assert names == ["Eco.Math.C89", "Eco.StdIO.C89", "Eco.Logger1", "CalcController"]


def test_parse_plan_extracts_sources():
    result = parse_plan(SAMPLE_PRD)
    sources = [c["source"] for c in result["components"]]
    assert sources == ["sdk", "sdk", "marketplace", "develop"]


def test_parse_plan_extracts_spec_for_develop():
    result = parse_plan(SAMPLE_PRD)
    develop = [c for c in result["components"] if c["source"] == "develop"][0]
    assert "Add(a,b)" in develop["spec"]


def test_parse_plan_extracts_platform_and_output():
    result = parse_plan(SAMPLE_PRD)
    assert result["platform"] == "Windows"
    assert result["output"] == "calc.exe"


def test_parse_plan_returns_empty_components_on_garbage():
    result = parse_plan("just some prose, no markdown structure")
    assert result["components"] == []
    assert result["project_name"] == ""


def test_parse_plan_does_not_attach_spec_to_sdk_component():
    """Regression: spec line must NOT bind to non-develop bullets."""
    md = """\
## Project: X

## Components

- **Eco.Math.C89** — source: sdk — math
  - spec: this should NOT attach to Math.C89
- **Custom1** — source: develop — glue
"""
    result = parse_plan(md)
    math = next(c for c in result["components"] if c["name"] == "Eco.Math.C89")
    custom = next(c for c in result["components"] if c["name"] == "Custom1")
    assert math["spec"] is None, "sdk component must not receive spec"
    assert custom["spec"] is None, "develop component without spec line stays None"


def test_parse_plan_handles_mixed_dash_styles():
    """Em-dash and ASCII hyphen must both work, even mixed on the same line."""
    md = """\
## Project: Y

## Components

- **A** - source: sdk - hyphen-only
- **B** — source: sdk — em-dash-only
- **C** — source: sdk - mixed
"""
    result = parse_plan(md)
    names = [c["name"] for c in result["components"]]
    assert names == ["A", "B", "C"]


def test_parse_plan_handles_optional_reason():
    """Component bullets without trailing reason must still parse."""
    md = """\
## Project: Z

## Components

- **NoReason** — source: sdk
"""
    result = parse_plan(md)
    assert len(result["components"]) == 1
    assert result["components"][0]["name"] == "NoReason"
    assert result["components"][0]["reason"] == ""


def test_parse_plan_extracts_multiple_develop_specs():
    """Two develop components, each with own spec line."""
    md = """\
## Project: Multi

## Components

- **A** — source: develop — first
  - spec: spec for A
- **B** — source: develop — second
  - spec: spec for B
"""
    result = parse_plan(md)
    a = next(c for c in result["components"] if c["name"] == "A")
    b = next(c for c in result["components"] if c["name"] == "B")
    assert a["spec"] == "spec for A"
    assert b["spec"] == "spec for B"


def test_parse_plan_handles_platform_with_spaces():
    """Platform value with whitespace must be preserved."""
    md = """\
## Project: P

## Build target

- Platform: Mac OS
- Output: my app.exe
"""
    result = parse_plan(md)
    assert result["platform"] == "Mac OS"
    assert result["output"] == "my app.exe"


from agent.parsers import parse_feedback


SAMPLE_FEEDBACK_BUILD = """\
## Stage: build
## Status: FAIL

## Errors
- src/EcoMain.c:42: error C2065: 'IEcoMath' undeclared identifier
- src/EcoMain.c:55: error C2143: missing ';' before identifier

## Suggested focus
- Forgot #include "IEcoMath.h"
"""

SAMPLE_FEEDBACK_TEST = """\
## Stage: test
## Status: FAIL

## Test failures
- test_calc_add: expected 5, got 4
- test_calc_sub: expected 2, got 0
"""


def test_parse_feedback_build_stage():
    result = parse_feedback(SAMPLE_FEEDBACK_BUILD)
    assert result["stage"] == "build"
    assert result["status"] == "FAIL"
    assert len(result["errors"]) == 2
    assert result["errors"][0]["file"] == "src/EcoMain.c"
    assert result["errors"][0]["line"] == 42
    assert "C2065" in result["errors"][0]["message"]


def test_parse_feedback_test_stage():
    result = parse_feedback(SAMPLE_FEEDBACK_TEST)
    assert result["stage"] == "test"
    assert len(result["test_failures"]) == 2
    assert result["test_failures"][0]["test"] == "test_calc_add"
    assert "expected 5" in result["test_failures"][0]["message"]


def test_parse_feedback_empty_input():
    result = parse_feedback("")
    assert result["errors"] == []
    assert result["test_failures"] == []
    assert result["stage"] == ""
