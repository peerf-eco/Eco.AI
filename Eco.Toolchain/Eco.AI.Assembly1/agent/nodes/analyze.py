"""
Node: analyze_request

Анализирует запрос пользователя и извлекает:
- Намерение (что хочет создать)
- Требуемые фичи (logging, arithmetic, file_io...)
- Целевую платформу
- Тип приложения
"""

import json
from typing import Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage

from ..prompts import ANALYZE_SYSTEM_PROMPT, get_analyze_user_prompt


def analyze_request(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """
    Анализирует запрос пользователя.
    
    Args:
        state: Текущее состояние агента
        llm: Языковая модель для анализа
        
    Returns:
        Обновления состояния: user_intent, required_features, target_platform, app_type
    """
    
    print("[ANALYZE] Starting request analysis...")
    
    # Получаем последнее сообщение пользователя
    messages = state.get("messages", [])
    if not messages:
        print("[ANALYZE] No messages found, using defaults")
        return {
            "user_intent": "Неизвестно",
            "required_features": ["component_bus"],
            "target_platform": "windows_x64",
            "app_type": "console_app"
        }
    
    user_message = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
    print(f"[ANALYZE] User message: {user_message[:100]}...")
    
    # Вызываем LLM для анализа
    response = llm.invoke([
        SystemMessage(content=ANALYZE_SYSTEM_PROMPT),
        HumanMessage(content=get_analyze_user_prompt(user_message))
    ])
    
    print(f"[ANALYZE] LLM response received, parsing...")
    
    # Парсим JSON ответ
    try:
        # Убираем возможные markdown-обёртки
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        parsed = json.loads(content)
        
        features = parsed.get("features", [])
        # component_bus нужен ВСЕГДА
        if "component_bus" not in features:
            features.append("component_bus")
        
        result = {
            "user_intent": parsed.get("intent", "Создание приложения"),
            "required_features": features,
            "target_platform": parsed.get("platform", "windows_x64"),
            "app_type": parsed.get("app_type", "console_app")
        }
        
        print(f"[ANALYZE] Intent: {result['user_intent']}")
        print(f"[ANALYZE] Features: {result['required_features']}")
        print(f"[ANALYZE] Platform: {result['target_platform']}")
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"[ANALYZE] [WARN] Failed to parse LLM response: {e}")
        print(f"[ANALYZE] [DEBUG] Response was: {response.content[:200]}...")
        
        # Fallback - базовый анализ
        return {
            "user_intent": user_message[:100],
            "required_features": ["component_bus", "logging"],
            "target_platform": "windows_x64",
            "app_type": "console_app"
        }


def create_analyze_node(llm):
    """
    Создаёт узел анализа с привязанной LLM.
    
    Использование:
        analyze_node = create_analyze_node(llm)
        graph.add_node("analyze_request", analyze_node)
    """
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        return analyze_request(state, llm)
    return node
