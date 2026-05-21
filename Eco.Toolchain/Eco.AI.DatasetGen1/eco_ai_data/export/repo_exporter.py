from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set


def sanitize_repo_id(name: str) -> str:
    s = re.sub(r"[^\w.\-]+", "_", name.strip())
    return s or "repository"


def flatten_entry_rows(entry: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
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
        row: Dict[str, Any] = {
            "question": q,
            "context": c,
            "answer": a,
            "repo": repo,
            "file": file_path,
        }
        qt = qa.get("question_type")
        if isinstance(qt, str) and qt.strip():
            row["question_type"] = qt.strip()
        rows.append(row)
    return rows


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def dedupe_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for row in rows:
        q = (row.get("question") or "").strip()
        a = (row.get("answer") or "").strip()
        key = hashlib.sha256(f"{q}\n{a}".encode()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def per_file_dataset_path(repo_dir: Path, file_rel: str) -> Path:
    rel = file_rel.replace("\\", "/")
    return repo_dir / f"{rel}.jsonl"


def combined_dataset_path(repo_dir: Path, repo_id: str) -> Path:
    return repo_dir / f"{repo_id}.jsonl"


def export_repo_datasets(
    entries: List[Dict[str, Any]],
    *,
    repo_id: str,
    output_base: Path,
    dedupe_combined: bool = True,
) -> Dict[str, Any]:
    """
    outputs/<repo_id>/
      <mirror>/<source>.jsonl
      <repo_id>.jsonl
    """
    safe_id = sanitize_repo_id(repo_id)
    repo_dir = output_base / safe_id
    repo_dir.mkdir(parents=True, exist_ok=True)

    all_rows: List[Dict[str, Any]] = []
    per_file_paths: List[str] = []

    for entry in entries:
        rows = flatten_entry_rows(entry)
        if not rows:
            continue
        rel = str(entry.get("file", "unknown")).replace("\\", "/")
        out_path = per_file_dataset_path(repo_dir, rel)
        write_jsonl(out_path, rows)
        per_file_paths.append(str(out_path))
        all_rows.extend(rows)

    combined_rows = dedupe_rows(all_rows) if dedupe_combined else all_rows
    combined_path = combined_dataset_path(repo_dir, safe_id)
    write_jsonl(combined_path, combined_rows)

    return {
        "repo_id": safe_id,
        "repo_dir": str(repo_dir),
        "combined_dataset": str(combined_path),
        "combined_rows": len(combined_rows),
        "per_file_count": len(per_file_paths),
        "per_file_paths": per_file_paths,
    }
