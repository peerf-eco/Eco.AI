from typing import Any, Dict, Iterable, List


class EntityNormalizer:
    def normalize(self, entities: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for entity in entities:
            normalized = dict(entity)
            normalized["type"] = str(normalized.get("type", "")).upper()
            normalized["name"] = str(normalized.get("name", "")).strip()
            if "class" in normalized:
                normalized["class"] = str(normalized["class"]).strip()
            if "function" in normalized:
                normalized["function"] = str(normalized["function"]).strip()
            out.append(normalized)
        return out
