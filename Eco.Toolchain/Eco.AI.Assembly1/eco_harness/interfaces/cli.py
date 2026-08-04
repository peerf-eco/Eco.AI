from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from agent.config.loader import load_config, load_role_config
from agent.main import get_model
from eco_harness.roles import make_role_agent
from eco_harness.worktrees import WorktreeInfo, create_worktree


class HarnessRunner:
    def __init__(self, root: Path | None = None) -> None:
        self.config = load_config(root)

    def run(
        self,
        request: str,
        *,
        language: str | None = None,
        mode: str = "create",
        use_worktree: bool = False,
        worktree_name: str | None = None,
    ) -> dict[str, Any]:
        worktree: WorktreeInfo | None = None
        if use_worktree:
            worktree = create_worktree(
                self.config.root,
                "cli-run",
                name=worktree_name,
                root=self.config.worktree_root,
            )
            project_dir = worktree.path
        else:
            project_dir = self.config.root / "output" / "cli-run"
        project_dir.mkdir(parents=True, exist_ok=True)
        role_name = "tester" if mode == "test" else "reviewer" if mode == "review" else "architect"
        _, spec, profile = load_role_config(role_name, self.config.root)
        backend_name = spec.backend.removesuffix("_cli")
        model = (
            get_model(profile, role=role_name)
            if backend_name in {"internal", "builtin", "eco"}
            else None
        )
        mode_spec = self.config.modes.get(mode)
        if mode_spec is None:
            raise ValueError(f"Unsupported mode: {mode}")
        agent = make_role_agent(
            role_name,
            config=self.config,
            model=model,
            cli_path=Path(self.config.eco_cli_path) if self.config.eco_cli_path else None,
            project_dir=project_dir,
            make_exe=Path("make"),
            language=language or self.config.default_language,
            marketplace_cache_root=self.config.root / "marketplace_cache",
            mode=mode,
        )
        result = agent.run(request)
        return {
            "status": result.status,
            "edge": result.stop_tool_name,
            "message": result.stop_payload,
            "error": result.error,
            "mode": mode,
            "worktree": str(worktree.path) if worktree else None,
        }


def main() -> int:
    import sys

    argv = sys.argv[1:]
    slash_mode = None
    if argv and argv[0].startswith("/"):
        slash_mode = argv.pop(0).lstrip("/").lower()
        argv = ["run", *argv, "--mode", slash_mode]
    sys.argv = [sys.argv[0], *argv]
    parser = argparse.ArgumentParser(prog="eco-harness")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("request")
    run_parser.add_argument("--language", default=None)
    run_parser.add_argument(
        "--mode",
        choices=["create", "migrate", "test", "review"],
        default="create",
    )
    run_parser.add_argument("--worktree", action="store_true")
    run_parser.add_argument("--worktree-name", default=None)
    run_parser.add_argument("--config-root", type=Path, default=None)
    serve_parser = subparsers.add_parser("serve")
    serve_parser.add_argument("--api", action="store_true")
    args = parser.parse_args()
    if args.command == "run":
        result = HarnessRunner(args.config_root).run(
            args.request,
            language=args.language,
            mode=args.mode,
            use_worktree=args.worktree,
            worktree_name=args.worktree_name,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result["status"] == "done" else 1
    if args.api:
        import uvicorn

        uvicorn.run("backend.server:app", host="0.0.0.0", port=8000)
        return 0
    parser.error("serve currently supports --api")
    return 2