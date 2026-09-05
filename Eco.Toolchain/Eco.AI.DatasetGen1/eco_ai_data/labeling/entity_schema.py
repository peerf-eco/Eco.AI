from enum import Enum
from typing import Any, Dict


# EntityType — перечисление, представляющее типы сущностей, которые могут встречаться в коде,
# например, функции, классы, импорты, методы, параметры, возвращаемые значения и переменные.
class EntityType(str, Enum):
    FUNCTION = "FUNCTION"
    CLASS = "CLASS"
    STRUCT = "STRUCT"
    UNION = "UNION"
    ENUM = "ENUM"
    TYPEDEF = "TYPEDEF"
    NAMESPACE = "NAMESPACE"
    TEMPLATE = "TEMPLATE"
    IMPORT = "IMPORT"
    METHOD = "METHOD"
    PARAMETER = "PARAMETER"
    RETURN = "RETURN"
    VARIABLE = "VARIABLE"


def is_valid_entity(entity: Dict[str, Any]) -> bool:
    entity_type = entity.get("type")
    name = entity.get("name")
    if not isinstance(entity_type, str) or not isinstance(name, str):
        return False
    if entity_type not in {e.value for e in EntityType}:
        return False
    if not name.strip():
        return False
    return True
