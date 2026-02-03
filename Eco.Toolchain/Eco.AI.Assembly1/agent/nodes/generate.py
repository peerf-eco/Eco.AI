"""
Node: generate_code

Генерирует C-код на основе:
- Выбранных компонентов
- Заголовков из RAG (точные сигнатуры!)
- Примеров использования
- Шаблонов кода
"""

from typing import Dict, Any, List
from langchain_core.messages import HumanMessage, SystemMessage

from ..prompts import GENERATE_SYSTEM_PROMPT, get_generate_user_prompt


def generate_code(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """
    Генерирует код на основе контекста из RAG.
    
    Args:
        state: Состояние с компонентами и контекстом
        llm: Языковая модель
        
    Returns:
        generated_files - список сгенерированных файлов
    """
    
    print("[GENERATE] Starting code generation...")
    
    user_intent = state.get("user_intent", "приложение")
    selected_components = state.get("selected_components", [])
    headers = state.get("retrieved_headers", {})
    examples = state.get("retrieved_examples", {})
    patterns = state.get("code_patterns", {})
    platform = state.get("target_platform", "windows_x64")
    
    print(f"[GENERATE] Intent: {user_intent}")
    print(f"[GENERATE] Components: {len(selected_components)}")
    print(f"[GENERATE] Headers loaded: {len(headers)}")
    print(f"[GENERATE] Examples loaded: {len(examples)}")
    
    # Формируем контекст для LLM
    context = build_context(
        selected_components,
        headers,
        examples,
        patterns
    )
    
    # Запрос к LLM
    user_prompt = get_generate_user_prompt(user_intent, platform, context)
    
    print("[GENERATE] Calling LLM...")
    
    response = llm.invoke([
        SystemMessage(content=GENERATE_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt)
    ])
    
    print("[GENERATE] LLM response received, parsing files...")
    
    # Парсим файлы из ответа
    generated_files = parse_generated_files(response.content)
    
    print(f"[GENERATE] Generated {len(generated_files)} files")
    for f in generated_files:
        print(f"[GENERATE]   - {f['path']} ({f['file_type']})")
    
    return {"generated_files": generated_files}


def build_context(
    components: List[Dict],
    headers: Dict[str, str],
    examples: Dict[str, str],
    patterns: Dict[str, str]
) -> str:
    """Формирует контекст для генерации кода"""
    
    context_parts = []
    
    # Добавляем заголовки (КРИТИЧЕСКИ ВАЖНО!)
    context_parts.append("═══ ЗАГОЛОВОЧНЫЕ ФАЙЛЫ (используй точные сигнатуры!) ═══")
    for name, content in headers.items():
        context_parts.append(f"\n--- {name} ---\n{content}")
    
    # Добавляем примеры
    if examples:
        context_parts.append("\n═══ ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ ═══")
        for name, code in examples.items():
            context_parts.append(f"\n--- Пример {name} ---\n{code}")
    
    # Добавляем шаблоны
    if patterns:
        context_parts.append("\n═══ ШАБЛОНЫ КОДА ═══")
        for name, pattern in patterns.items():
            if pattern:
                context_parts.append(f"\n--- {name} ---\n{pattern}")
    
    # Информация о компонентах
    context_parts.append("\n═══ ВЫБРАННЫЕ КОМПОНЕНТЫ ═══")
    for comp in components:
        context_parts.append(f"""
Компонент: {comp['name']}
CID: {comp['cid']}
Interface: {comp['interface_name']}
IID: {comp['iid']}
Методы: {comp.get('methods', {})}
""")
    
    return "\n".join(context_parts)


def parse_generated_files(content: str) -> List[Dict[str, str]]:
    """
    Парсит сгенерированные файлы из ответа LLM.
    
    Формат:
    ---FILE: path/to/file.c---
    content
    ---END FILE---
    """
    
    files = []
    current_file = None
    current_content = []
    
    for line in content.split('\n'):
        if line.startswith('---FILE:'):
            # Начало нового файла
            if current_file:
                files.append({
                    "path": current_file,
                    "content": '\n'.join(current_content),
                    "file_type": get_file_type(current_file)
                })
            current_file = line.replace('---FILE:', '').replace('---', '').strip()
            current_content = []
        elif line.strip() == '---END FILE---':
            # Конец файла
            if current_file:
                files.append({
                    "path": current_file,
                    "content": '\n'.join(current_content),
                    "file_type": get_file_type(current_file)
                })
            current_file = None
            current_content = []
        elif current_file:
            current_content.append(line)
    
    # Последний файл (если нет END FILE)
    if current_file and current_content:
        files.append({
            "path": current_file,
            "content": '\n'.join(current_content),
            "file_type": get_file_type(current_file)
        })
    
    return files


def get_file_type(path: str) -> str:
    """Определяет тип файла по расширению"""
    if path.endswith('.c'):
        return 'source'
    elif path.endswith('.h'):
        return 'header'
    elif path.endswith('.bat') or path.endswith('.sh'):
        return 'build'
    else:
        return 'other'


def create_generate_node(llm):
    """Создаёт узел генерации с привязанной LLM"""
    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        return generate_code(state, llm)
    return node
