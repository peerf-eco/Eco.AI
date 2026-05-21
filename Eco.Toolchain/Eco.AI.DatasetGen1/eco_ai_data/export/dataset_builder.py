from typing import Any, Dict, Iterable, List


class DatasetBuilder:
    def build_entry(
        self,
        repo: str,
        file_path: str,
        entities: List[Dict[str, Any]],
        qa_pairs: List[Dict[str, str]],
        raw_code: str,
    ) -> Dict[str, Any]:
        return {
            "repo": repo,
            "file": file_path,
            "entities": entities,
            "qa_pairs": qa_pairs,
            "raw_code": raw_code,
        }

    def to_hf_dataset(self, entries: Iterable[Dict[str, Any]]):
        try:
            from datasets import Dataset
        except Exception:
            return None
        return Dataset.from_list(list(entries))
