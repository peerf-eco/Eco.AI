from collections import Counter
from typing import Any, Dict, Iterable


class MetricsReport:
    def build(self, entries: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        total_files = 0
        total_entities = 0
        total_qa_pairs = 0
        entity_counter = Counter()
        files_with_empty_entities = 0
        files_with_empty_qa = 0
        entities_missing_line = 0
        entities_missing_optional_context = 0
        duplicate_counter = Counter()
        question_type_counter: Counter[str] = Counter()
        for entry in entries:
            total_files += 1
            entities = entry.get("entities", [])
            qa_pairs = entry.get("qa_pairs", [])
            total_entities += len(entities)
            total_qa_pairs += len(qa_pairs)
            if len(entities) == 0:
                files_with_empty_entities += 1
            if len(qa_pairs) == 0:
                files_with_empty_qa += 1
            for qa in qa_pairs:
                if isinstance(qa, dict):
                    qt = qa.get("question_type")
                    if isinstance(qt, str) and qt.strip():
                        question_type_counter[qt.strip()] += 1
            file_path = str(entry.get("file", ""))
            for entity in entities:
                entity_counter[str(entity.get("type", "UNKNOWN"))] += 1
                if entity.get("line") is None:
                    entities_missing_line += 1
                if entity.get("class") is None and entity.get("function") is None:
                    entities_missing_optional_context += 1
                duplicate_key = (
                    file_path,
                    entity.get("type"),
                    entity.get("name"),
                    entity.get("class"),
                    entity.get("function"),
                    entity.get("line"),
                )
                duplicate_counter[duplicate_key] += 1
        duplicate_entities = sum(v - 1 for v in duplicate_counter.values() if v > 1)
        return {
            "files": total_files,
            "entities": total_entities,
            "qa_pairs": total_qa_pairs,
            "entity_types": dict(entity_counter),
            "data_quality": {
                "files_with_empty_entities": files_with_empty_entities,
                "files_with_empty_qa_pairs": files_with_empty_qa,
                "entities_missing_line": entities_missing_line,
                "entities_without_class_or_function": entities_missing_optional_context,
                "duplicate_entities": duplicate_entities,
                "qa_question_types": dict(question_type_counter),
            },
        }
