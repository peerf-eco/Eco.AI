import argparse
from pathlib import Path

from eco_ai_data.config import PipelineConfig
from eco_ai_data.master_pipeline import EcoAIDataPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eco-ai-data",
        description="Generation dataset (instruction-to-code, ACOM).",
    )
    parser.add_argument("--tool", choices=["ast", "c_ast", "regex", "openai"], default="ast")
    parser.add_argument("--processes", type=int, default=0)
    parser.add_argument("--output-dir", default="outputs", help="Base dir; creates outputs/<repo_name>/...")
    parser.add_argument("--strict-python-only", action="store_true")
    parser.add_argument("--strict-c-cpp-only", action="store_true")
    parser.add_argument("--openai-model", default="gpt-4o-mini")
    parser.add_argument("--openai-api-key", default="")
    parser.add_argument(
        "--no-qa-openai",
        action="store_true",
        help="Do not call OpenAI for generated context text.",
    )
    parser.add_argument(
        "--context",
        action="store_true",
        help="Include context field (OpenAI or fallback template).",
    )
    parser.add_argument(
        "--max-qa-pairs",
        type=int,
        default=None,
        metavar="N",
        help="Per source file: stop after N generation samples. Omit for no limit.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    analyze = sub.add_parser("analyze", help="Analyze repo → outputs/<repo_name>/...")
    analyze.add_argument("repo_path_or_url")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    config = PipelineConfig(
        tool_name=args.tool,
        processes=args.processes,
        output_dir=args.output_dir,
        dataset_mode="generation",
        strict_python_only=args.strict_python_only,
        strict_c_cpp_only=args.strict_c_cpp_only,
        openai_model=args.openai_model,
        openai_api_key=args.openai_api_key or None,
        qa_answers_via_openai=not args.no_qa_openai,
        include_context=args.context,
        max_qa_pairs_per_file=args.max_qa_pairs if args.max_qa_pairs is not None and args.max_qa_pairs > 0 else None,
    )
    pipeline = EcoAIDataPipeline(config=config)
    if args.command == "analyze":
        result = pipeline.analyze_and_export(args.repo_path_or_url)
        for key, value in result.items():
            print(f"{key}={value}")
        return


if __name__ == "__main__":
    main()
