import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


class JsonExporter:
    def export(self, entries: Iterable[Dict], output_path: Path, output_format: str = "json") -> None:
        fmt = output_format.lower().strip()
        if fmt not in {"json", "jsonl"}:
            raise ValueError(f"Unsupported output format: {output_format}. Supported formats: json, jsonl")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            if fmt == "json":
                f.write("[\n")
                first = True
                for entry in entries:
                    if not first:
                        f.write(",\n")
                    first = False
                    f.write(json.dumps(entry, ensure_ascii=False))
                f.write("\n]\n")
                return

            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False))
                f.write("\n")

    def load(self, input_path: Path, input_format: str) -> List[Dict[str, Any]]:
        fmt = input_format.lower().strip()
        if fmt not in {"json", "jsonl"}:
            raise ValueError(f"Unsupported input format: {input_format}. Supported formats: json, jsonl")
        if fmt == "json":
            data = json.loads(input_path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError("JSON dataset must be a list of entries")
            out: List[Dict[str, Any]] = []
            for item in data:
                if isinstance(item, dict):
                    out.append(item)
                else:
                    raise ValueError("JSON dataset contains non-object entry")
            return out

        out: List[Dict[str, Any]] = []
        for line in input_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError("JSONL dataset contains non-object entry")
            out.append(item)
        return out

    def validate_entries(self, entries: Iterable[Dict[str, Any]]) -> Dict[str, int]:
        entry_count = 0
        entity_count = 0
        qa_count = 0
        invalid_entries = 0
        invalid_entities = 0
        for entry in entries:
            entry_count += 1
            if not isinstance(entry, dict):
                invalid_entries += 1
                continue
            if "repo" not in entry or "file" not in entry or "entities" not in entry or "qa_pairs" not in entry:
                invalid_entries += 1
                continue
            entities = entry.get("entities", [])
            qa_pairs = entry.get("qa_pairs", [])
            if not isinstance(entities, list) or not isinstance(qa_pairs, list):
                invalid_entries += 1
                continue
            entity_count += len(entities)
            qa_count += len(qa_pairs)
            for entity in entities:
                if not isinstance(entity, dict):
                    invalid_entities += 1
                    continue
                entity_type = entity.get("type")
                entity_name = entity.get("name")
                if not isinstance(entity_type, str) or not entity_type.strip():
                    invalid_entities += 1
                if not isinstance(entity_name, str) or not entity_name.strip():
                    invalid_entities += 1
        if invalid_entries > 0 or invalid_entities > 0:
            raise ValueError(
                f"Invalid exported dataset: invalid_entries={invalid_entries}, invalid_entities={invalid_entities}"
            )
        return {
            "entries": entry_count,
            "entities": entity_count,
            "qa_pairs": qa_count,
            "invalid_entries": invalid_entries,
            "invalid_entities": invalid_entities,
        }
