from typing import Any, Dict, Iterable, List, Tuple


class EntityDeduplicator:
    def deduplicate(self, entities: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen: set[Tuple[Any, ...]] = set()
        out: List[Dict[str, Any]] = []
        for entity in entities:
            key = (
                entity.get("type"),
                entity.get("name"),
                entity.get("class"),
                entity.get("function"),
                entity.get("line"),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(entity)
        return out
