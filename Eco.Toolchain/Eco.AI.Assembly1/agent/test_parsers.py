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
