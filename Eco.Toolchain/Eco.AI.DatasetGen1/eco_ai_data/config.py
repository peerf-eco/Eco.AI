from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class PipelineConfig:
    max_file_bytes: int = 2_000_000
    include_extensions: List[str] = field(
        default_factory=lambda: [
            ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h", ".cs", ".go", ".rs", ".php", ".rb", ".swift", ".kt", ".scala", ".sh", ".bash", ".zsh", ".sql"
        ]
    )
    exclude_dirs: List[str] = field(
        default_factory=lambda: [
            ".git",
            ".hg",
            ".svn",
            "__pycache__",
            ".venv",
            "venv",
            ".mypy_cache",
            ".pytest_cache",
            "build",
            "dist",
            "site-packages",
            "node_modules",
        ]
    )
    processes: int = 0
    tool_name: str = "ast"
    strict_python_only: bool = False
    strict_c_cpp_only: bool = False
    output_format: str = "json"
    openai_model: str = "gpt-4o-mini"
    openai_api_key: Optional[str] = None
    dataset_mode: str = "generation"
    qa_answers_via_openai: bool = True
    max_qa_pairs_per_file: Optional[int] = None
    include_context: bool = False
    chunk_chars: int = 8000
    output_dir: str = "outputs"

    def __post_init__(self) -> None:
        if self.strict_python_only and self.strict_c_cpp_only:
            raise ValueError("strict_python_only and strict_c_cpp_only cannot be enabled together")
        if self.strict_python_only:
            self.include_extensions = [".py"]
        elif self.strict_c_cpp_only or self.tool_name == "c_ast":
            self.include_extensions = [".c", ".h", ".hpp", ".hh", ".hxx", ".cpp", ".cc", ".cxx"]
        self.dataset_mode = str(self.dataset_mode).lower().strip()
        if self.dataset_mode not in {"generation", "documentation"}:
            raise ValueError("dataset_mode must be 'generation' or 'documentation'")
        self.output_format = str(self.output_format).lower().strip()
        if self.output_format not in {"json", "jsonl"}:
            raise ValueError("output_format must be 'json' or 'jsonl'")

    def output_path(self) -> Path:
        path = Path(self.output_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path
