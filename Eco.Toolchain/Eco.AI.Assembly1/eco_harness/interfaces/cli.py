from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from agent.config.loader import load_config, load_role_config
from agent.main import get_model
from eco_harness.roles import make_role_agent


class HarnessRunner:
    def __init__(self, root: Path | None = None) -> None:
        self.config = load_config(root)

    def run(self, request: str, *, language: str | None = None) -> dict[str, Any]:
        project_dir = self.config.root / "output" / "cli-run"
        project_dir.mkdir(parents=True, exist_ok=True)
        _, spec, profile = load_role_config("architect", self.config.root)
        backend_name = spec.backend.removesuffix("_cli")
        model = get_model(profile, role="architect") if backend_name == "internal" else None
        agent = make_role_agent(
            "architect",
            config=self.config,
            model=model,
            cli_path=Path(self.config.eco_cli_path) if self.config.eco_cli_path else None,
            project_dir=project_dir,
            make_exe=Path("make"),
            language=language or self.config.default_language,
            marketplace_cache_root=self.config.root / "marketplace_cache",
        )
        result = agent.run(request)
        return {
            "status": result.status,
            "edge": result.stop_tool_name,
            "message": result.stop_payload,
            "error": result.error,
        }


def main() -> int:
    parser = argparse.ArgumentParser(prog="eco-harness")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("request")
    run_parser.add_argument("--language", default=None)
    run_parser.add_argument("--config-root", type=Path, default=None)
    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--api", action="store_true")
    args = parser.parse_args()
    if args.command == "run":
        result = HarnessRunner(args.config_root).run(
            args.request,
            language=args.language,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["status"] == "done" else 1
    if args.api:
        import uvicorn

        uvicorn.run("backend.server:app", host="0.0.0.0", port=8000)
        return 0
    parser.error("serve currently supports --api")
    return 2