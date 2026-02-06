"""
Node: select_components

Выбирает компоненты EcoOS на основе требуемых фич.
Использует маппинг фича → компонент и загружает спецификации.
"""

from typing import Dict, Any, List
from ..knowledge_base import get_component_spec, FEATURE_TO_COMPONENTS


def select_components(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Выбирает необходимые компоненты на основе required_features.
    
    Логика:
    1. Для каждой фичи определяем, какие компоненты нужны
    2. Eco.InterfaceBus1 добавляется ВСЕГДА (это шина для всех компонентов)
    3. Загружаем спецификации компонентов из Knowledge Base
    4. Разрешаем зависимости (если A зависит от B, добавляем B)
    
    Args:
        state: Текущее состояние агента
        
    Returns:
        Обновления состояния: selected_components
    """
    
    required_features = state.get("required_features", [])
    
    # ═══════════════════════════════════════════════════════════════
    # ШАГ 1: Маппинг фич → компоненты
    # ═══════════════════════════════════════════════════════════════
    
    required_component_names = set()
    
    for feature in required_features:
        components = FEATURE_TO_COMPONENTS.get(feature, [])
        required_component_names.update(components)
    
    # InterfaceBus1 нужен ВСЕГДА
    required_component_names.add("Eco.InterfaceBus1")
    
    print(f"[SELECT] Required features: {required_features}")
    print(f"[SELECT] Mapped to components: {required_component_names}")
    
    # ═══════════════════════════════════════════════════════════════
    # ШАГ 2: Загружаем спецификации компонентов
    # ═══════════════════════════════════════════════════════════════
    
    components = []
    
    for name in required_component_names:
        spec = get_component_spec(name)
        if spec:
            components.append(spec.model_dump())
            print(f"[SELECT] Loaded spec for: {name}")
        else:
            print(f"[SELECT] WARNING: No spec found for: {name}")
    
    # ═══════════════════════════════════════════════════════════════
    # ШАГ 3: Разрешаем зависимости
    # ═══════════════════════════════════════════════════════════════
    
    resolved_names = {c["name"] for c in components}
    
    for comp in list(components):  # Копия для итерации
        for dep_name in comp.get("dependencies", []):
            if dep_name not in resolved_names:
                dep_spec = get_component_spec(dep_name)
                if dep_spec:
                    components.append(dep_spec.model_dump())
                    resolved_names.add(dep_name)
                    print(f"[SELECT] Added dependency: {dep_name}")
    
    # ═══════════════════════════════════════════════════════════════
    # ШАГ 4: Сортируем по порядку инициализации
    # ═══════════════════════════════════════════════════════════════
    
    # InterfaceBus1 должен быть первым
    components.sort(key=lambda c: 0 if c["name"] == "Eco.InterfaceBus1" else 1)
    
    return {"selected_components": components}

