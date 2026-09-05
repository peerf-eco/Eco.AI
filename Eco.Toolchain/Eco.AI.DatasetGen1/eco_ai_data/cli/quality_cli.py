import argparse
import json
from pathlib import Path

from eco_ai_data.quality.dataset_quality import analyze_dataset_paths, render_markdown_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eco-ai-data-quality",
        description="Evaluate instruction-to-code dataset quality (completeness, alignment, duplication, diversity).",
    )
    parser.add_argument(
        "dataset_path",
        help="Path to outputs/<repo_name>/ or a single .jsonl file.",
    )
    parser.add_argument(
        "--output-json",
        default="",
        help="Write full JSON report to this path.",
    )
    parser.add_argument(
        "--output-md",
        default="",
        help="Write Markdown summary to this path.",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Print JSON report to stdout.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    root = Path(args.dataset_path)
    if not root.exists():
        raise SystemExit(f"Path does not exist: {root}")

    out_json = Path(args.output_json).expanduser().resolve() if args.output_json else None
    out_md = Path(args.output_md).expanduser().resolve() if args.output_md else None
    if not out_json and not out_md and not args.print_json:
        if root.is_dir():
            reports_dir = root / "reports"
        else:
            reports_dir = root.parent / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        out_json = reports_dir / "quality_report.json"
        out_md = reports_dir / "quality_report.md"

    report = analyze_dataset_paths([root], output_json=out_json, output_md=out_md)

    print(f"samples={report.get('samples', 0)}")
    print(f"overall_score={report.get('overall_score')} grade={report.get('grade')}")
    for k, v in (report.get("subscores") or {}).items():
        print(f"  {k}: {v}")
    if out_json:
        print(str(out_json))
    if out_md:
        print(str(out_md))
    if args.print_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
