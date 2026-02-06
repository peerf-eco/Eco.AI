"""
Node: review_code

Проверяет сгенерированный код на:
- Синтаксические ошибки
- Соответствие сигнатурам из заголовков
- Наличие обязательных паттернов (cleanup, error handling)
- Правильность вызовов через pVTbl

═══════════════════════════════════════════════════════════════════════════
ВАЖНО: Это статическая проверка кода.

Для полной валидации нужен ВНЕШНИЙ ИНСТРУМЕНТ:
1. Компиляция через cl.exe / gcc
2. Линковка с DLL
3. Запуск и проверка результата

Этот узел НЕ компилирует код - он делает статический анализ.
═══════════════════════════════════════════════════════════════════════════
"""

import re
import json
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, SystemMessage

from ..prompts import REVIEW_SYSTEM_PROMPT, get_review_user_prompt


# Паттерны для проверки кода
VALIDATION_RULES = [
    {
        "name": "vtbl_call_pattern",
        "description": "Вызов методов должен быть через pVTbl",
        "pattern": r"->pVTbl->",
        "required": True,
        "error_if_missing": "Методы интерфейса должны вызываться через pVTbl"
    },
    {
        "name": "self_as_first_arg",
        "description": "Первый аргумент метода - сам объект",
        "pattern": r"pVTbl->\w+\s*\(\s*\w+",
        "required": True,
        "error_if_missing": "Первый аргумент метода должен быть указателем на объект"
    },
    {
        "name": "release_cleanup",
        "description": "Должен быть Release для освобождения ресурсов",
        "pattern": r"->pVTbl->Release\s*\(",
        "required": True,
        "error_if_missing": "Отсутствует Release() для освобождения ресурсов"
    },
    {
        "name": "error_check",
        "description": "Проверка результата операций",
        "pattern": r"(ERR_ECO_OK|!= 0|== 0)",
        "required": True,
        "error_if_missing": "Отсутствует проверка кодов ошибок"
    },
    {
        "name": "factory_signature",
        "description": "Правильная сигнатура GetIEcoComponentFactoryPtr",
        "pattern": r"IEcoComponentFactory\s*\*\s*\w+\s*=\s*GetIEcoComponentFactoryPtr\s*\(\s*\)",
        "required": False,
        "error_if_missing": None
    },
    {
        "name": "wrong_factory_call",
        "description": "НЕПРАВИЛЬНЫЙ вызов фабрики с out-параметром",
        "pattern": r"GetIEcoComponentFactoryPtr\s*\(\s*&",
        "required": False,
        "error_if_present": "ОШИБКА: GetIEcoComponentFactoryPtr возвращает указатель напрямую, не через out-параметр!"
    },
]


def validate_code_static(files: List[Dict]) -> List[Dict]:
    """
    Статическая валидация сгенерированного кода.
    
    Проверяет паттерны в исходных файлах (.c).
    """
    
    errors = []
    
    for file in files:
        if file["file_type"] != "source":
            continue
        
        content = file["content"]
        file_path = file["path"]
        
        for rule in VALIDATION_RULES:
            pattern = rule["pattern"]
            found = bool(re.search(pattern, content))
            
            # Проверяем обязательные паттерны
            if rule["required"] and not found and rule.get("error_if_missing"):
                errors.append({
                    "file": file_path,
                    "line": None,
                    "message": rule["error_if_missing"],
                    "severity": "warning"
                })
            
            # Проверяем запрещённые паттерны
            if found and rule.get("error_if_present"):
                # Находим строку с ошибкой
                for i, line in enumerate(content.split('\n'), 1):
                    if re.search(pattern, line):
                        errors.append({
                            "file": file_path,
                            "line": i,
                            "message": rule["error_if_present"],
                            "severity": "error"
                        })
                        break
    
    return errors


def review_code(state: Dict[str, Any], llm=None) -> Dict[str, Any]:
    """
    Проверяет сгенерированный код.
    
    Выполняет:
    1. Статическую валидацию по паттернам
    2. (Опционально) LLM-проверку на соответствие заголовкам
    
    Args:
        state: Состояние с generated_files
        llm: LLM для семантической проверки (опционально)
        
    Returns:
        validation_errors, is_valid
    """
    
    print("[REVIEW] Starting code review...")
    
    generated_files = state.get("generated_files", [])
    iteration_count = state.get("iteration_count", 0) + 1
    max_iterations = state.get("max_iterations", 3)
    
    # ═══════════════════════════════════════════════════════════════
    # 1. Статическая валидация
    # ═══════════════════════════════════════════════════════════════
    
    print("[REVIEW] Running static validation...")
    errors = validate_code_static(generated_files)
    print(f"[REVIEW] Static validation found {len(errors)} issues")
    
    # ═══════════════════════════════════════════════════════════════
    # 2. LLM-проверка (если передана модель)
    # ═══════════════════════════════════════════════════════════════
    
    if llm and state.get("retrieved_headers"):
        print("[REVIEW] Running LLM validation...")
        llm_errors = validate_with_llm(
            generated_files, 
            state.get("retrieved_headers", {}),
            llm
        )
        errors.extend(llm_errors)
        print(f"[REVIEW] LLM validation found {len(llm_errors)} additional issues")
    
    # ═══════════════════════════════════════════════════════════════
    # 3. Определяем валидность
    # ═══════════════════════════════════════════════════════════════
    
    # Считаем только errors, не warnings
    critical_errors = [e for e in errors if e["severity"] == "error"]
    is_valid = len(critical_errors) == 0
    
    # Если превышен лимит итераций - принимаем как есть
    if iteration_count >= max_iterations:
        print(f"[REVIEW] Max iterations ({max_iterations}) reached, accepting code")
        is_valid = True
    
    print(f"[REVIEW] Iteration {iteration_count}/{max_iterations}")
    print(f"[REVIEW] Errors: {len(critical_errors)}, Warnings: {len(errors) - len(critical_errors)}")
    print(f"[REVIEW] Is valid: {is_valid}")
    
    return {
        "validation_errors": errors,
        "is_valid": is_valid,
        "iteration_count": iteration_count,
    }


def validate_with_llm(files: List[Dict], headers: Dict[str, str], llm) -> List[Dict]:
    """
    Семантическая проверка кода с помощью LLM.
    
    Проверяет соответствие сигнатурам из заголовков.
    """
    
    source_files = [f for f in files if f["file_type"] == "source"]
    if not source_files:
        return []
    
    code = source_files[0]["content"]
    headers_text = "\n\n".join([f"// {name}\n{content}" for name, content in headers.items()])
    
    prompt = get_review_user_prompt(headers_text, code)
    
    try:
        response = llm.invoke([
            SystemMessage(content=REVIEW_SYSTEM_PROMPT),
            HumanMessage(content=prompt)
        ])
        content = response.content.strip()
        
        # Парсим JSON
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        
        return json.loads(content)
    except Exception as e:
        print(f"[REVIEW] LLM validation failed: {e}")
        return []


def create_review_node(llm=None):
    """Создаёт узел проверки, опционально с LLM"""
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        return review_code(state, llm)
    return node
