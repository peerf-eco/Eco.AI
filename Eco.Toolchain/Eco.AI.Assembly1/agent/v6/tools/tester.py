"""TESTER tools — run_artifact + report_test_pass/fail. No read_file by design."""
from __future__ import annotations
import json
import subprocess
from pathlib import Path
from pydantic import BaseModel, Field
from agent.v6.eco_agent import EcoTool, ToolResult


class RunArtifactArgs(BaseModel):
    timeout_s: int = Field(default=10, ge=1, le=60)


class ReportTestPassArgs(BaseModel):
    reason_md: str = Field(..., description="Why the artifact satisfies the user request")


class ReportTestFailArgs(BaseModel):
    reason_md: str = Field(..., description="Specifically what does not match expectations")


def _run_artifact(args: RunArtifactArgs, build_artifact: Path) -> ToolResult:
    if not build_artifact.exists():
        return ToolResult(content=f"artifact does not exist: {build_artifact}", is_error=True)
    try:
        proc = subprocess.run(
            [str(build_artifact)],
            shell=False,
            capture_output=True,
            text=True,
            timeout=args.timeout_s,
        )
        payload = {
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as e:
        payload = {
            "exit_code": None,
            "stdout": (e.stdout or b"").decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or ""),
            "stderr": (e.stderr or b"").decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or ""),
            "timed_out": True,
        }
    return ToolResult(content=json.dumps(payload, ensure_ascii=False), details=payload)


def make_tester_tools(*, build_artifact: Path) -> list[EcoTool]:
    return [
        EcoTool("run_artifact", "Run the built artifact and capture stdout/stderr/exit/timeout.",
                RunArtifactArgs, lambda a: _run_artifact(a, build_artifact)),
        EcoTool("report_test_pass", "Stop tool. Call when the artifact behaves as the user asked.",
                ReportTestPassArgs, lambda _a: ToolResult(content="(stop)")),
        EcoTool("report_test_fail", "Stop tool. Call when the artifact does NOT match expectations.",
                ReportTestFailArgs, lambda _a: ToolResult(content="(stop)")),
    ]
