from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from eco_harness.adapters.protocol import AgentResult, EventSink


_HANDOFF_RE = re.compile(
    r"<eco-handoff\s+edge=['\"](?P<edge>[^'\"]+)['\"]>(?P<body>.*?)</eco-handoff>",
    re.DOTALL | re.IGNORECASE,
)


class ExternalCliBackend:
    _FLAGS = {"codex": "-p", "pi": "-e", "claude": "-p"}

    def __init__(
        self,
        name: str,
        *,
        executable: str | None = None,
        cwd: Path | None = None,
        timeout_s: int = 900,
    ) -> None:
        self.name = name
        self.executable = executable or name
        self.cwd = cwd
        self.timeout_s = timeout_s

    def supports_tools(self) -> bool:
        return False

    def _resolve_executable(self) -> str:
        configured = Path(self.executable)
        if configured.is_file():
            return str(configured)
        resolved = shutil.which(self.executable)
        if resolved:
            return resolved
        raise FileNotFoundError(
            f"External agent '{self.name}' was not found. "
            f"Install it or set ECO_{self.name.upper()}_PATH to its executable."
        )

    def run(
        self,
        *,
        role: str,
        seed: str,
        budget: Any,
        on_event: EventSink | None = None,
    ) -> AgentResult:
        try:
            executable = self._resolve_executable()
        except FileNotFoundError as error:
            return AgentResult(status="error", edge=None, message="", error=str(error))

        flag = self._FLAGS.get(self.name)
        if flag is None:
            return AgentResult(
                status="error",
                edge=None,
                message="",
                error=f"Unsupported external agent '{self.name}'.",
            )
        prompt = (
            f"You are the {role} role in an ACOM meta-harness. "
            "Perform the assigned work in the workspace. "
            "When finished, emit exactly one marker in this format: "
            "<eco-handoff edge=\"to_coder|to_tester|done|fail|to_architect\">"
            "your concise handoff</eco-handoff>. "
            "Do not put generated boilerplate in chat; use eco-wizard. "
            f"\n\n{seed}"
        )
        command = [executable, flag, prompt]
        if on_event:
            on_event({"type": "start", "role": role, "backend": self.name})
        try:
            process = subprocess.run(
                command,
                cwd=str(self.cwd) if self.cwd else None,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                timeout=getattr(budget, "max_wall_s", None) or self.timeout_s,
                env=os.environ.copy(),
            )
        except subprocess.TimeoutExpired:
            message = f"{self.name} timed out after {self.timeout_s}s."
            if on_event:
                on_event({"type": "error", "role": role, "message": message})
            return AgentResult(status="error", edge=None, message="", error=message)
        except OSError as error:
            return AgentResult(
                status="error",
                edge=None,
                message="",
                error=f"{self.name} failed to start: {error}",
            )

        output = (process.stdout or "").strip()
        if process.returncode != 0:
            output = output or (process.stderr or "").strip()
            return AgentResult(
                status="error",
                edge=None,
                message=output,
                error=f"{self.name} exited with code {process.returncode}",
            )
        match = _HANDOFF_RE.search(output)
        if not match:
            return AgentResult(
                status="no_tool_call",
                edge=None,
                message=output,
                error=(
                    f"{self.name} completed without a structured "
                    "<eco-handoff> marker."
                ),
            )
        edge = match.group("edge").strip()
        message = match.group("body").strip()
        if on_event:
            on_event({"type": "done", "role": role, "edge": edge, "message": message})
        return AgentResult(status="done", edge=edge, message=message)