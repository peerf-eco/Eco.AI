import json
from multiprocessing import Pool, cpu_count
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple

from eco_ai_data.config import PipelineConfig
from eco_ai_data.export.dataset_builder import DatasetBuilder
from eco_ai_data.export.repo_exporter import export_repo_datasets
from eco_ai_data.labeling.label_engine import LabelEngine
from eco_ai_data.postprocessing.deduplicator import EntityDeduplicator
from eco_ai_data.postprocessing.normalizer import EntityNormalizer
from eco_ai_data.postprocessing.validator import EntityValidator
from eco_ai_data.preprocessing.code_cleaner import CodeCleaner
from eco_ai_data.preprocessing.file_filter import FileFilter
from eco_ai_data.preprocessing.repo_loader import RepoLoader, RepoSource
from eco_ai_data.quality.dataset_quality import DatasetQualityAnalyzer, render_markdown_report
from eco_ai_data.reporting.markdown_report import MarkdownReport
from eco_ai_data.reporting.metrics_report import MetricsReport


def _read_file_text(path: str) -> Tuple[str, str]:
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
        return path, text
    except UnicodeDecodeError:
        try:
            text = p.read_text(encoding="latin-1")
            return path, text
        except Exception:
            return path, ""
    except Exception:
        return path, ""


class EcoAIDataPipeline:
    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()
        self.repo_loader = RepoLoader()
        self.file_filter = FileFilter(
            include_extensions=self.config.include_extensions,
            exclude_dirs=self.config.exclude_dirs,
            max_file_bytes=self.config.max_file_bytes,
        )
        self.code_cleaner = CodeCleaner()
        self.label_engine = LabelEngine(
            tool_name=self.config.tool_name,
            openai_model=self.config.openai_model,
            openai_api_key=self.config.openai_api_key or "",
            dataset_mode=self.config.dataset_mode,
            qa_answers_via_openai=self.config.qa_answers_via_openai,
            max_qa_pairs_per_file=self.config.max_qa_pairs_per_file,
            include_context=self.config.include_context,
        )
        self.validator = EntityValidator()
        self.deduplicator = EntityDeduplicator()
        self.normalizer = EntityNormalizer()
        self.dataset_builder = DatasetBuilder()
        self.markdown_report = MarkdownReport()
        self.metrics_report = MetricsReport()
        self._repo_source: RepoSource | None = None
        self._last_entries: List[Dict[str, Any]] = []
        self._last_repo_id: str = ""
        self._last_repo_dir: Path | None = None

    def analyze(self, repo_path_or_url: str) -> List[Dict[str, Any]]:
        source = self.repo_loader.load(repo_path_or_url)
        self._repo_source = source
        self._last_repo_id = source.repo_id
        entries = list(self._iter_entries(source))
        self._last_entries = entries
        return entries

    def analyze_and_export(self, repo_path_or_url: str) -> Dict[str, str]:
        entries = self.analyze(repo_path_or_url)
        output_base = self.config.output_path()
        export_info = export_repo_datasets(
            entries,
            repo_id=self._last_repo_id,
            output_base=output_base,
            dedupe_combined=True,
        )
        repo_dir = Path(export_info["repo_dir"])
        reports_dir = repo_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        self._last_repo_dir = repo_dir

        metrics = self.metrics_report.build(entries)
        pipeline_md = reports_dir / "pipeline_report.md"
        self.markdown_report.generate(self._last_repo_id, metrics, self.config.tool_name, pipeline_md)

        combined_path = Path(export_info["combined_dataset"])
        rows = []
        if combined_path.is_file():
            for line in combined_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rows.append(json.loads(line))
        quality = DatasetQualityAnalyzer(rows=rows).analyze()
        quality_json = reports_dir / "quality_report.json"
        quality_md = reports_dir / "quality_report.md"
        quality_json.write_text(json.dumps(quality, ensure_ascii=False, indent=2), encoding="utf-8")
        quality_md.write_text(render_markdown_report(quality), encoding="utf-8")

        self._safe_cleanup_repo()
        return {
            "repo_dir": str(repo_dir),
            "combined_dataset": export_info["combined_dataset"],
            "combined_rows": str(export_info["combined_rows"]),
            "per_file_count": str(export_info["per_file_count"]),
            "pipeline_report": str(pipeline_md),
            "quality_report_json": str(quality_json),
            "quality_report_md": str(quality_md),
        }

    def to_hf_dataset(self):
        if not self._last_entries:
            return None
        return self.dataset_builder.to_hf_dataset(self._last_entries)

    def _iter_entries(self, source: RepoSource) -> Iterator[Dict[str, Any]]:
        paths = [p for p in self.file_filter.iter_python_files(source.root_path)]
        processes = self._resolve_processes()
        if processes <= 1:
            for p in paths:
                _, raw = _read_file_text(str(p))
                entry = self._process_file(source, p, raw)
                if entry is not None:
                    yield entry
            return
        with Pool(processes=processes) as pool:
            for path_str, raw in pool.imap_unordered(_read_file_text, [str(p) for p in paths], chunksize=16):
                p = Path(path_str)
                entry = self._process_file(source, p, raw)
                if entry is not None:
                    yield entry

    def _process_file(self, source: RepoSource, path: Path, raw: str) -> Dict[str, Any] | None:
        if not raw:
            return None
        cleaned = self.code_cleaner.clean(raw)
        entities = self.label_engine.label(cleaned)
        entities = self.validator.validate(entities)
        entities = self.deduplicator.deduplicate(entities)
        entities = self.normalizer.normalize(entities)
        qa_pairs = self.label_engine.generate_qa_pairs(cleaned, file_path=str(path))
        file_rel = str(path.relative_to(source.root_path))
        return self.dataset_builder.build_entry(
            repo=source.repo_id,
            file_path=file_rel,
            entities=entities,
            qa_pairs=qa_pairs,
            raw_code=cleaned,
        )

    def _resolve_processes(self) -> int:
        if self.config.processes and self.config.processes > 0:
            return self.config.processes
        return max(1, min(cpu_count(), 8))

    def _safe_cleanup_repo(self) -> None:
        if self._repo_source:
            self._repo_source.cleanup()
            self._repo_source = None
