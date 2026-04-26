from typing import Any, Dict, Iterable, List


class EntityValidator:
    def validate(self, entities: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for entity in entities:
            if not isinstance(entity, dict):
                continue
            entity_type = entity.get("type")
            name = entity.get("name")
            if not isinstance(entity_type, str) or not entity_type.strip():
                continue
            if not isinstance(name, str) or not name.strip():
                continue
            out.append(entity)
        return out
