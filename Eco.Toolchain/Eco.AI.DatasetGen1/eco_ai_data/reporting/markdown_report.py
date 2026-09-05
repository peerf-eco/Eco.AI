from pathlib import Path
from typing import Any, Dict


class MarkdownReport:
    def generate(self, repo: str, metrics: Dict[str, Any], tool_name: str, output_path: Path) -> None:
        lines = [
            "# Eco.AI.Data Report",
            "",
            "## Repo summary",
            "",
            f"- Repository: `{repo}`",
            f"- Analyzer tool: `{tool_name}`",
            f"- Files processed: {metrics.get('files', 0)}",
            "",
            "## Entity statistics",
            "",
            f"- Total entities: {metrics.get('entities', 0)}",
            f"- Total QA pairs: {metrics.get('qa_pairs', 0)}",
            "",
            "## Tool comparison metrics",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Files | {metrics.get('files', 0)} |",
            f"| Entities | {metrics.get('entities', 0)} |",
            f"| QA pairs | {metrics.get('qa_pairs', 0)} |",
            "",
            "## Error analysis",
            "",
            "- Parsing failures are skipped safely during streaming iteration.",
            "- Invalid entities are removed during validation and normalization.",
            "",
            "## Entity type breakdown",
            "",
            "| Type | Count |",
            "|---|---:|",
        ]
        entity_types = metrics.get("entity_types", {})
        for key in sorted(entity_types.keys()):
            lines.append(f"| {key} | {entity_types[key]} |")
        lines.append("")

        quality = metrics.get("data_quality", {})
        if isinstance(quality, dict):
            lines.extend(
                [
                    "## Data Quality",
                    "",
                    f"- Files with empty entities: {quality.get('files_with_empty_entities', 0)}",
                    f"- Files with empty QA pairs: {quality.get('files_with_empty_qa_pairs', 0)}",
                    f"- Entities missing line: {quality.get('entities_missing_line', 0)}",
                    f"- Entities without class/function context: {quality.get('entities_without_class_or_function', 0)}",
                    f"- Duplicate entities: {quality.get('duplicate_entities', 0)}",
                    "",
                ]
            )
            qt = quality.get("qa_question_types") if isinstance(quality, dict) else None
            if isinstance(qt, dict) and qt:
                lines.extend(["### QA question types", ""])
                for k in sorted(qt.keys()):
                    lines.append(f"- `{k}`: {qt[k]}")
                lines.append("")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines), encoding="utf-8")
