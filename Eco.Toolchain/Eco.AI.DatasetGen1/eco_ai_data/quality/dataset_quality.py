"""
Оценка качества instruction-to-code датасета (ACOM / IMPLEMENTATION).

Метрики основаны на практиках instruction tuning и code LLM datasets:
- Quality / completeness (Li et al., 2024; OpenCodeInstruct, 2025)
- Diversity & redundancy (Data Diversity Matters, EMNLP 2024; NovelSum, 2025)
- Instruction-response alignment (How Do Your Code LLMs Perform?, 2024)
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

_REQUIRED_FIELDS = ("question", "answer")
_OPTIONAL_FIELDS = ("context", "repo", "file", "question_type")

_ACOM_MARKER = "ACOM component-based architecture"
_SIGNATURE_MARKER = "The signature is:"
_IMPLEMENTATION = "IMPLEMENTATION"

_FALLBACK_CONTEXT_MARKERS = (
    "Function receives parameters declared in the signature",
    "Function receives required inputs defined by the signature",
)

_HEDGE_RE = re.compile(
    r"\b(likely|probably|presumably|possibly|seemingly)\b|"
    r"\bit\s+seems\b|"
    r"\bappears\s+to\b",
    re.IGNORECASE,
)

_C_FUNC_NAME_RE = re.compile(
    r"(?:^|[\s*&])([~A-Za-z_]\w*(?:::[~A-Za-z_]\w*)*)\s*\(",
)


def _read_jsonl_rows(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        item = json.loads(line)
        if isinstance(item, dict):
            rows.append(item)
        elif isinstance(item, dict) is False:
            # pipeline format: expand qa_pairs
            pass
    return rows


def _load_pipeline_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        if "qa_pairs" in entry and isinstance(entry.get("qa_pairs"), list):
            repo = entry.get("repo", "")
            file_path = entry.get("file", "")
            for qa in entry["qa_pairs"]:
                row = dict(qa)
                row.setdefault("repo", repo)
                row.setdefault("file", file_path)
                rows.append(row)
        elif isinstance(entry, dict):
            rows.append(entry)
    return rows


def load_dataset_rows(path: Path) -> List[Dict[str, Any]]:
    if path.is_dir():
        combined = path / f"{path.name}.jsonl"
        if combined.is_file():
            return _read_jsonl_rows(combined)
        rows: List[Dict[str, Any]] = []
        for f in sorted(path.rglob("*.jsonl")):
            if "reports" in f.parts:
                continue
            rows.extend(_read_jsonl_rows(f))
        return rows
    if path.name == "pipeline.jsonl":
        return _load_pipeline_jsonl(path)
    try:
        head = path.read_text(encoding="utf-8")[:500]
        if "qa_pairs" in head:
            return _load_pipeline_jsonl(path)
    except OSError:
        pass
    return _read_jsonl_rows(path)


def _extract_signature_from_question(question: str) -> str:
    if _SIGNATURE_MARKER not in question:
        return ""
    part = question.split(_SIGNATURE_MARKER, 1)[1].strip()
    part = part.replace("{ ... }", "").strip()
    return " ".join(part.split())


def _extract_func_name(signature: str) -> str:
    m = _C_FUNC_NAME_RE.search(signature)
    if not m:
        return ""
    return m.group(1)


def _normalize_text(text: str) -> str:
    return " ".join(text.split())


def _brace_balanced(code: str) -> bool:
    depth = 0
    for ch in code:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def _percentile(values: Sequence[int], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = (len(ordered) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(ordered[int(k)])
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def _shannon_entropy(counts: Counter) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    ent = 0.0
    for n in counts.values():
        p = n / total
        if p > 0:
            ent -= p * math.log2(p)
    return ent


@dataclass
class DatasetQualityAnalyzer:
    rows: List[Dict[str, Any]] = field(default_factory=list)

    def analyze(self) -> Dict[str, Any]:
        n = len(self.rows)
        if n == 0:
            return {"samples": 0, "overall_score": 0.0, "error": "empty dataset"}

        structural = self._structural_metrics()
        instruction = self._instruction_metrics()
        alignment = self._alignment_metrics()
        code = self._code_heuristic_metrics()
        context = self._context_metrics()
        duplication = self._duplication_metrics()
        diversity = self._diversity_metrics()
        distribution = self._distribution_metrics()

        subscores = {
            "structural_validity": structural["score"],
            "instruction_format": instruction["score"],
            "answer_alignment": alignment["score"],
            "code_heuristics": code["score"],
            "context_quality": context["score"],
            "deduplication": duplication["score"],
            "diversity": diversity["score"],
        }
        weights = {
            "structural_validity": 0.20,
            "instruction_format": 0.15,
            "answer_alignment": 0.20,
            "code_heuristics": 0.15,
            "context_quality": 0.10,
            "deduplication": 0.10,
            "diversity": 0.10,
        }
        overall = sum(subscores[k] * weights[k] for k in weights)

        return {
            "samples": n,
            "overall_score": round(overall, 2),
            "grade": _grade(overall),
            "subscores": {k: round(v, 2) for k, v in subscores.items()},
            "weights": weights,
            "metrics": {
                "structural": structural,
                "instruction": instruction,
                "alignment": alignment,
                "code_heuristics": code,
                "context": context,
                "duplication": duplication,
                "diversity": diversity,
                "distribution": distribution,
            },
            "issues_sample": self._collect_issue_samples(limit=15),
            "references": [
                "Wang et al. (2024) How Do Your Code LLMs Perform? — instruction complexity, response quality, diversity",
                "Li et al. (2024) Data Diversity Matters for Robust Instruction Tuning — quality, diversity, redundancy",
                "OpenCodeInstruct (2025) — filtering & LLM quality assessment for code datasets",
            ],
        }

    def _structural_metrics(self) -> Dict[str, Any]:
        n = len(self.rows)
        missing = 0
        empty_q = 0
        empty_a = 0
        bad_type = 0
        for row in self.rows:
            for f in _REQUIRED_FIELDS:
                if f not in row or not str(row.get(f, "")).strip():
                    missing += 1
                    break
            if not str(row.get("question", "")).strip():
                empty_q += 1
            if not str(row.get("answer", "")).strip():
                empty_a += 1
            qt = row.get("question_type")
            if qt is not None and str(qt).strip() and str(qt).strip() != _IMPLEMENTATION:
                bad_type += 1
        valid_rate = 1.0 - (missing / n)
        score = 100.0 * valid_rate
        return {
            "score": score,
            "missing_required_rate": round(missing / n, 4),
            "empty_question_rate": round(empty_q / n, 4),
            "empty_answer_rate": round(empty_a / n, 4),
            "non_implementation_type_count": bad_type,
        }

    def _instruction_metrics(self) -> Dict[str, Any]:
        n = len(self.rows)
        has_acom = 0
        has_sig_marker = 0
        has_extractable_sig = 0
        for row in self.rows:
            q = str(row.get("question", ""))
            if _ACOM_MARKER in q:
                has_acom += 1
            if _SIGNATURE_MARKER in q:
                has_sig_marker += 1
            if _extract_signature_from_question(q):
                has_extractable_sig += 1
        rate = (has_acom + has_sig_marker + has_extractable_sig) / (3 * n)
        return {
            "score": round(100.0 * rate, 2),
            "acom_prompt_rate": round(has_acom / n, 4),
            "signature_marker_rate": round(has_sig_marker / n, 4),
            "extractable_signature_rate": round(has_extractable_sig / n, 4),
        }

    def _alignment_metrics(self) -> Dict[str, Any]:
        n = len(self.rows)
        name_in_answer = 0
        sig_prefix_match = 0
        checked = 0
        for row in self.rows:
            q = str(row.get("question", ""))
            a = str(row.get("answer", ""))
            sig = _extract_signature_from_question(q)
            if not sig:
                continue
            checked += 1
            fname = _extract_func_name(sig)
            if fname and fname in a:
                name_in_answer += 1
            sig_head = sig.split("(")[0].strip()
            if sig_head and a.lstrip().startswith(sig_head):
                sig_prefix_match += 1
        if checked == 0:
            return {"score": 0.0, "checked": 0}
        rate = (name_in_answer + sig_prefix_match) / (2 * checked)
        return {
            "score": round(100.0 * rate, 2),
            "checked_samples": checked,
            "function_name_in_answer_rate": round(name_in_answer / checked, 4),
            "answer_starts_with_signature_rate": round(sig_prefix_match / checked, 4),
        }

    def _code_heuristic_metrics(self) -> Dict[str, Any]:
        n = len(self.rows)
        has_braces = 0
        balanced = 0
        min_lines = 0
        for row in self.rows:
            a = str(row.get("answer", ""))
            if "{" in a and "}" in a:
                has_braces += 1
            if _brace_balanced(a):
                balanced += 1
            if len(a.splitlines()) >= 3:
                min_lines += 1
        rate = (has_braces + balanced + min_lines) / (3 * n)
        return {
            "score": round(100.0 * rate, 2),
            "has_braces_rate": round(has_braces / n, 4),
            "balanced_braces_rate": round(balanced / n, 4),
            "min_3_lines_rate": round(min_lines / n, 4),
        }

    def _context_metrics(self) -> Dict[str, Any]:
        n = len(self.rows)
        empty = 0
        fallback = 0
        hedge = 0
        for row in self.rows:
            c = str(row.get("context") or "").strip()
            if not c:
                empty += 1
            elif any(m in c for m in _FALLBACK_CONTEXT_MARKERS):
                fallback += 1
            if c and _HEDGE_RE.search(c):
                hedge += 1
        non_empty = n - empty
        ai_like = non_empty - fallback
        # Если context опционален, пустой не штрафуем сильно; штрафуем fallback и hedge
        if non_empty == 0:
            score = 100.0
        else:
            score = 100.0 * (1.0 - (fallback + hedge) / non_empty)
        return {
            "score": round(max(0.0, score), 2),
            "empty_context_rate": round(empty / n, 4),
            "fallback_context_rate": round(fallback / n, 4),
            "ai_like_context_rate": round(ai_like / n, 4),
            "hedge_words_in_context_count": hedge,
        }

    def _duplication_metrics(self) -> Dict[str, Any]:
        n = len(self.rows)
        answer_hashes: Counter = Counter()
        pair_hashes: Counter = Counter()
        for row in self.rows:
            a = _normalize_text(str(row.get("answer", "")))
            q = _normalize_text(str(row.get("question", "")))
            answer_hashes[hashlib.sha256(a.encode()).hexdigest()] += 1
            pair_hashes[hashlib.sha256(f"{q}\n{a}".encode()).hexdigest()] += 1
        dup_answers = sum(1 for c in answer_hashes.values() if c > 1)
        dup_pairs = sum(1 for c in pair_hashes.values() if c > 1)
        redundant_rows = sum(c - 1 for c in answer_hashes.values() if c > 1)
        dup_rate = redundant_rows / n if n else 0.0
        score = max(0.0, 100.0 * (1.0 - dup_rate))
        return {
            "score": round(score, 2),
            "unique_answers": len(answer_hashes),
            "duplicate_answer_groups": dup_answers,
            "duplicate_pair_groups": dup_pairs,
            "redundant_rows_from_answer_dup": redundant_rows,
            "answer_duplication_rate": round(dup_rate, 4),
        }

    def _diversity_metrics(self) -> Dict[str, Any]:
        n = len(self.rows)
        files: Counter = Counter()
        lessons: Counter = Counter()
        funcs: Counter = Counter()
        for row in self.rows:
            fp = str(row.get("file", ""))
            files[fp] += 1
            lesson = fp.split("/")[0] if fp else "unknown"
            lessons[lesson] += 1
            sig = _extract_signature_from_question(str(row.get("question", "")))
            fn = _extract_func_name(sig) or "unknown"
            funcs[fn] += 1
        file_ent = _shannon_entropy(files)
        lesson_ent = _shannon_entropy(lessons)
        func_ent = _shannon_entropy(funcs)
        # нормализуем энтропию к [0,1] через log2(unique)
        def norm_ent(ent: float, unique: int) -> float:
            if unique <= 1:
                return 0.0
            return ent / math.log2(unique)

        file_div = norm_ent(file_ent, len(files))
        lesson_div = norm_ent(lesson_ent, len(lessons))
        func_div = norm_ent(func_ent, len(funcs))
        score = 100.0 * (file_div + lesson_div + func_div) / 3.0
        top_funcs = funcs.most_common(10)
        return {
            "score": round(score, 2),
            "unique_source_files": len(files),
            "unique_lessons": len(lessons),
            "unique_function_names": len(funcs),
            "file_entropy_normalized": round(file_div, 4),
            "lesson_entropy_normalized": round(lesson_div, 4),
            "function_entropy_normalized": round(func_div, 4),
            "top_repeated_function_names": [(k, v) for k, v in top_funcs if v > 1],
        }

    def _distribution_metrics(self) -> Dict[str, Any]:
        ans_lens = [len(str(r.get("answer", ""))) for r in self.rows]
        ctx_lens = [len(str(r.get("context") or "")) for r in self.rows]
        per_file = Counter(str(r.get("file", "")) for r in self.rows)
        per_lesson: Counter = Counter()
        for fp, cnt in per_file.items():
            lesson = fp.split("/")[0] if fp else "unknown"
            per_lesson[lesson] += cnt
        return {
            "answer_chars": {
                "min": min(ans_lens) if ans_lens else 0,
                "median": int(statistics.median(ans_lens)) if ans_lens else 0,
                "p90": int(_percentile(ans_lens, 0.9)),
                "max": max(ans_lens) if ans_lens else 0,
            },
            "context_chars": {
                "min": min(ctx_lens) if ctx_lens else 0,
                "median": int(statistics.median(ctx_lens)) if ctx_lens else 0,
                "p90": int(_percentile(ctx_lens, 0.9)),
                "max": max(ctx_lens) if ctx_lens else 0,
            },
            "samples_per_lesson": dict(per_lesson),
            "samples_per_file_max": max(per_file.values()) if per_file else 0,
        }

    def _collect_issue_samples(self, limit: int = 15) -> List[Dict[str, str]]:
        issues: List[Dict[str, str]] = []
        for i, row in enumerate(self.rows):
            q = str(row.get("question", ""))
            a = str(row.get("answer", ""))
            c = str(row.get("context") or "")
            fp = str(row.get("file", ""))
            if not q.strip() or not a.strip():
                issues.append({"index": str(i), "file": fp, "issue": "empty_question_or_answer"})
            sig = _extract_signature_from_question(q)
            fname = _extract_func_name(sig)
            if sig and fname and fname not in a:
                issues.append({"index": str(i), "file": fp, "issue": "function_name_not_in_answer"})
            if a and not _brace_balanced(a):
                issues.append({"index": str(i), "file": fp, "issue": "unbalanced_braces"})
            if c and any(m in c for m in _FALLBACK_CONTEXT_MARKERS):
                issues.append({"index": str(i), "file": fp, "issue": "fallback_context"})
            if len(issues) >= limit:
                break
        return issues


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def analyze_dataset_paths(
    paths: Sequence[Path],
    *,
    output_json: Optional[Path] = None,
    output_md: Optional[Path] = None,
) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    sources: List[str] = []
    for p in paths:
        p = p.expanduser().resolve()
        loaded = load_dataset_rows(p)
        rows.extend(loaded)
        sources.append(str(p))
    analyzer = DatasetQualityAnalyzer(rows=rows)
    report = analyzer.analyze()
    report["sources"] = sources
    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if output_md:
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(render_markdown_report(report), encoding="utf-8")
    return report


def render_markdown_report(report: Dict[str, Any]) -> str:
    lines = [
        "# Dataset Quality Report",
        "",
        f"- **Samples:** {report.get('samples', 0)}",
        f"- **Overall score:** {report.get('overall_score', 0)} / 100 ({report.get('grade', '?')})",
        "",
        "## Subscores",
        "",
        "| Dimension | Score |",
        "|---|---:|",
    ]
    for k, v in (report.get("subscores") or {}).items():
        lines.append(f"| {k} | {v} |")
    lines.extend(["", "## Key metrics", ""])
    metrics = report.get("metrics") or {}
    for section, data in metrics.items():
        lines.append(f"### {section}")
        if isinstance(data, dict):
            for kk, vv in data.items():
                if kk == "score":
                    continue
                lines.append(f"- `{kk}`: {vv}")
        lines.append("")
    issues = report.get("issues_sample") or []
    if issues:
        lines.append("## Sample issues")
        lines.append("")
        for it in issues:
            lines.append(f"- [{it.get('issue')}] file=`{it.get('file')}` index={it.get('index')}")
        lines.append("")
    refs = report.get("references") or []
    if refs:
        lines.append("## References")
        lines.append("")
        for r in refs:
            lines.append(f"- {r}")
        lines.append("")
    return "\n".join(lines)
