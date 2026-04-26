import argparse
import json
from pathlib import Path
from typing import Any

from eco_ai_data.config import PipelineConfig
from eco_ai_data.master_pipeline import EcoAIDataPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="eco-ai-data-doc")
    parser.add_argument("--tool", choices=["ast", "c_ast", "regex", "openai"], default="ast")
    parser.add_argument("--processes", type=int, default=0)
    parser.add_argument("--output-dir", default="outputs")
    parser.add_argument("--strict-python-only", action="store_true")
    parser.add_argument("--strict-c-cpp-only", action="store_true")
    parser.add_argument("--output-format", choices=["json", "jsonl"], default="json")
    parser.add_argument("--openai-model", default="gpt-4o-mini")
    parser.add_argument("--openai-api-key", default="")
    parser.add_argument(
        "--no-qa-openai",
        action="store_true",
        help="Do not call OpenAI for documentation QA answers.",
    )
    parser.add_argument(
        "--max-qa-pairs",
        type=int,
        default=None,
        metavar="N",
        help="Per source file: stop after N QA rows (documentation mode). Omit for no limit.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    analyze = sub.add_parser("analyze")
    analyze.add_argument("repo_path_or_url")
    analyze.add_argument("--output-json", default="")
    analyze.add_argument("--output-md", default="")

    qa_flatten = sub.add_parser(
        "qa-flatten",
        help="Flatten pipeline JSONL entries into question/context/answer rows.",
    )
    qa_flatten.add_argument("input_jsonl", help="Full pipeline JSONL")
    qa_flatten.add_argument("output_jsonl", help="Output JSONL with one QA object per line")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = PipelineConfig(
        tool_name=args.tool,
        processes=args.processes,
        output_dir=args.output_dir,
        dataset_mode="documentation",
        strict_python_only=args.strict_python_only,
        strict_c_cpp_only=args.strict_c_cpp_only,
        output_format=args.output_format,
        openai_model=args.openai_model,
        openai_api_key=args.openai_api_key or None,
        qa_answers_via_openai=not args.no_qa_openai,
        max_qa_pairs_per_file=args.max_qa_pairs if args.max_qa_pairs is not None and args.max_qa_pairs > 0 else None,
    )
    pipeline = EcoAIDataPipeline(config=config)
    if args.command == "analyze":
        default_name = "doc_dataset.jsonl" if args.output_format == "jsonl" else "doc_dataset.json"
        output_json = args.output_json or str(Path(args.output_dir) / default_name)
        output_md = args.output_md or str(Path(args.output_dir) / "doc_report.md")
        result = pipeline.analyze_export_report(
            repo_path_or_url=args.repo_path_or_url,
            output_json=output_json,
            output_md=output_md,
        )
        print(result["json"])
        print(result["report"])
        return
    if args.command == "qa-flatten":
        _qa_flatten(Path(args.input_jsonl), Path(args.output_jsonl))
        print(str(Path(args.output_jsonl).resolve()))
        return


def _qa_flatten(src: Path, dst: Path) -> None:
    rows = [x for x in src.read_text(encoding="utf-8").splitlines() if x.strip()]
    out: list[dict[str, Any]] = []
    for line in rows:
        entry = json.loads(line)
        repo = entry.get("repo", "")
        file_path = entry.get("file", "")
        for qa in entry.get("qa_pairs", []):
            q = (qa.get("question") or "").strip()
            c = qa.get("context")
            if c is None:
                c = ""
            else:
                c = str(c)
            a = (qa.get("answer") or "").strip()
            if not q or not a:
                continue
            row: dict[str, Any] = {
                "question": q,
                "context": c,
                "answer": a,
                "repo": repo,
                "file": file_path,
            }
            qt = qa.get("question_type")
            if isinstance(qt, str) and qt.strip():
                row["question_type"] = qt.strip()
            out.append(row)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8") as f:
        for item in out:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
