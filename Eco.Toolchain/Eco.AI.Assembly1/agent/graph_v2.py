"""
EcoOS Component Agent - Graph v2

Новая архитектура:
    PLANNER (ReAct) → BUILDER (ReAct) → QA → BUILD
         ↑                  ↑______________|
         |__________________|  (если ошибка)

Structured Output через Pydantic модели как tools.
"""

import json
import logging
from typing import Dict, Any, Literal, Annotated, List, Optional
from typing_extensions import TypedDict

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent, ToolNode
from langgraph.checkpoint.memory import MemorySaver

from .tools import PLANNER_TOOLS, BUILDER_TOOLS, QA_TOOLS, list_files, read_file, write_file, build
from .prompts_v2 import (
    PLANNER_SYSTEM_PROMPT, 
    BUILDER_SYSTEM_PROMPT, 
    QA_SYSTEM_PROMPT,
    get_planner_prompt,
    get_builder_prompt,
    get_qa_prompt
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS FOR STRUCTURED OUTPUT
# ═══════════════════════════════════════════════════════════════════════════

class MethodDefinition(BaseModel):
    """Описание метода интерфейса."""
    name: str = Field(description="Имя метода (например 'Addition', 'Subtraction')")
    params: str = Field(description="Параметры метода (например 'int16_t a, int16_t b')")
    return_type: str = Field(description="Тип возвращаемого значения (например 'int32_t')")
    description: str = Field(description="Описание что делает метод")


class PlannerResponse(BaseModel):
    """Структурированный ответ Planner агента с планом компонента.
    
    ВАЖНО: Вызови этот tool когда план готов!
    """
    component_name: str = Field(description="Имя компонента без Eco. префикса (например 'Calculator')")
    interface_name: str = Field(description="Имя интерфейса (например 'IEcoCalculatorX')")
    methods: List[MethodDefinition] = Field(description="Список методов интерфейса")
    dependencies: List[str] = Field(default_factory=list, description="Зависимости (CID компонентов)")
    files_to_create: List[str] = Field(description="Список путей файлов для создания")


class BuilderResponse(BaseModel):
    """Структурированный ответ Builder агента.
    
    ВАЖНО: Вызови этот tool когда все файлы созданы!
    """
    files_created: List[str] = Field(description="Список созданных файлов")
    project_name: str = Field(description="Имя проекта (например 'Eco.Calculator')")
    ready_for_build: bool = Field(description="Готов ли проект к сборке")


# ═══════════════════════════════════════════════════════════════════════════
# CONTEXT SUMMARIZATION
# ═══════════════════════════════════════════════════════════════════════════

SUMMARIZE_PROMPT = """Сожми следующую историю действий Builder агента в краткое summary.

Включи:
1. Какие файлы были созданы (список путей)
2. Какие примеры были прочитаны
3. Ключевые решения по коду

Формат ответа - ТОЛЬКО краткий текст (3-5 предложений), без JSON.

История действий:
{history}

Краткое summary:"""


def summarize_builder_context(llm, messages: list, files_created: list) -> str:
    """
    Сжимает историю сообщений Builder агента через LLM.
    
    Args:
        llm: Языковая модель
        messages: Список сообщений из builder_messages
        files_created: Список созданных файлов
    
    Returns:
        Сжатое summary контекста
    """
    logger.info(f"[SUMMARIZE] Starting context summarization...")
    logger.info(f"[SUMMARIZE] Messages count: {len(messages)}")
    logger.info(f"[SUMMARIZE] Files created: {len(files_created)}")
    
    # Собираем историю действий
    history_parts = []
    
    for msg in messages:
        msg_type = type(msg).__name__
        
        if msg_type == 'HumanMessage':
            # Пропускаем начальный промпт (слишком большой)
            content = str(msg.content)[:200] if hasattr(msg, 'content') else ""
            if content:
                history_parts.append(f"[USER] {content}...")
        
        elif msg_type == 'AIMessage':
            # Извлекаем tool calls
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_name = tc.get('name', 'unknown')
                    args = tc.get('args', {})
                    
                    if tool_name == 'read_file':
                        history_parts.append(f"[READ] {args.get('path', '?')}")
                    elif tool_name == 'write_file':
                        path = args.get('path', '?')
                        history_parts.append(f"[WRITE] {path}")
                    elif tool_name == 'list_files':
                        history_parts.append(f"[LIST] {args.get('path', '?')}")
                    elif tool_name == 'build':
                        history_parts.append(f"[BUILD] {args.get('project_name', '?')}")
        
        elif msg_type == 'ToolMessage':
            content = str(msg.content) if hasattr(msg, 'content') else ""
            # Только краткие результаты
            if "OK:" in content:
                history_parts.append(f"  → {content[:100]}")
            elif "ERROR:" in content:
                history_parts.append(f"  → ERROR: {content[7:150]}...")
    
    # Добавляем список файлов
    if files_created:
        history_parts.append(f"\nСозданные файлы: {', '.join(files_created)}")
    
    history_text = "\n".join(history_parts[-50:])  # Последние 50 записей
    
    logger.info(f"[SUMMARIZE] History text length: {len(history_text)} chars")
    
    # Если история короткая - не сжимаем
    if len(history_text) < 500:
        logger.info("[SUMMARIZE] History too short, using as-is")
        return f"Builder создал файлы: {', '.join(files_created)}"
    
    # Вызываем LLM для сжатия
    try:
        prompt = SUMMARIZE_PROMPT.format(history=history_text)
        response = llm.invoke(prompt)
        
        summary = response.content if hasattr(response, 'content') else str(response)
        summary = summary.strip()
        
        logger.info(f"[SUMMARIZE] Generated summary: {summary[:200]}...")
        
        return summary
        
    except Exception as e:
        logger.error(f"[SUMMARIZE] LLM call failed: {e}")
        # Fallback - простое summary
        return f"Builder создал {len(files_created)} файлов: {', '.join(files_created[:5])}..."


# ═══════════════════════════════════════════════════════════════════════════
# STATE
# ═══════════════════════════════════════════════════════════════════════════

class AgentStateV2(TypedDict):
    """Состояние агента v2."""
    
    # Входные данные
    user_request: str
    
    # Результат Planner (structured output)
    plan: Optional[PlannerResponse]
    planner_messages: Annotated[list, add_messages]
    
    # Результат Builder (structured output)
    builder_response: Optional[BuilderResponse]
    files_created: List[str]
    builder_messages: Annotated[list, add_messages]
    
    # Сжатый контекст Builder (для retry после ошибки)
    builder_context_summary: str
    
    # Результат QA/Build
    build_result: str
    is_success: bool
    error_message: str
    
    # Управление итерациями
    iteration: int
    max_iterations: int


# ═══════════════════════════════════════════════════════════════════════════
# PLANNER NODE (с structured output через tool)
# ═══════════════════════════════════════════════════════════════════════════

def create_planner_node(llm):
    """
    Создаёт Planner как ReAct агент со structured output.
    
    Использует PlannerResponse как tool для гарантированного
    структурированного вывода.
    """
    
    # Добавляем PlannerResponse как tool к списку инструментов
    planner_tools_with_response = PLANNER_TOOLS + [PlannerResponse]
    
    # Создаём ReAct агент
    # НЕ используем tool_choice - он конфликтует с create_react_agent
    planner_agent = create_react_agent(
        llm,
        tools=planner_tools_with_response,
        prompt=PLANNER_SYSTEM_PROMPT
    )
    
    def planner_node(state: AgentStateV2) -> Dict[str, Any]:
        logger.info("=" * 60)
        logger.info("[PLANNER] Starting with structured output...")
        logger.info(f"[PLANNER] User request: {state['user_request']}")
        logger.info(f"[PLANNER] Tools: {[t.name if hasattr(t, 'name') else t.__name__ for t in planner_tools_with_response]}")
        
        # Формируем входное сообщение
        user_prompt = get_planner_prompt(state["user_request"])
        
        # Цикл повторных попыток - если модель не вызвала PlannerResponse,
        # напоминаем ей и продолжаем
        max_retries = 3
        messages = []
        current_messages = [("user", user_prompt)]
        
        for attempt in range(max_retries):
            logger.info(f"[PLANNER] Attempt {attempt + 1}/{max_retries}")
            
            # Запускаем агент
            result = planner_agent.invoke(
                {"messages": current_messages},
                {"recursion_limit": 50}
            )
            
            messages = result.get("messages", [])
            logger.info(f"[PLANNER] Got {len(messages)} messages from agent")
            
            # Проверяем, был ли вызван PlannerResponse
            planner_response_called = False
            for msg in messages:
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        if tool_call.get('name') == 'PlannerResponse':
                            planner_response_called = True
                            break
                if planner_response_called:
                    break
            
            if planner_response_called:
                logger.info("[PLANNER] PlannerResponse was called, proceeding")
                break
            else:
                logger.warning(f"[PLANNER] PlannerResponse NOT called on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    # Добавляем напоминание и продолжаем с того же места
                    reminder = """ВАЖНО: Ты должен ОБЯЗАТЕЛЬНО вызвать tool PlannerResponse с планом!

Ты уже изучил примеры. Теперь вызови PlannerResponse tool с полями:
- component_name: имя компонента (например "SimpleCalculator")
- interface_name: имя интерфейса (например "IEcoSimpleCalculator")
- methods: список методов [{name, params, return_type, description}]
- files_to_create: ПОЛНЫЕ пути с Eco.{name}/ префиксом

Вызови PlannerResponse СЕЙЧАС!"""
                    current_messages = messages + [("user", reminder)]
                    logger.info("[PLANNER] Added reminder and retrying...")
        logger.info(f"[PLANNER] Got {len(messages)} messages from agent")
        
        # Ищем вызов PlannerResponse tool в сообщениях
        plan = None
        for msg in messages:
            # Логируем тип сообщения
            msg_type = type(msg).__name__
            logger.debug(f"[PLANNER] Message type: {msg_type}")
            
            # Проверяем tool_calls
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get('name', '')
                    logger.info(f"[PLANNER] Found tool call: {tool_name}")
                    
                    if tool_name == 'PlannerResponse':
                        # Извлекаем аргументы и создаём Pydantic модель
                        args = tool_call.get('args', {})
                        logger.info(f"[PLANNER] PlannerResponse args keys: {list(args.keys())}")
                        
                        try:
                            plan = PlannerResponse(**args)
                            logger.info(f"[PLANNER] Successfully parsed PlannerResponse!")
                            logger.info(f"[PLANNER] Component: {plan.component_name}")
                            logger.info(f"[PLANNER] Interface: {plan.interface_name}")
                            logger.info(f"[PLANNER] Methods count: {len(plan.methods)}")
                            logger.info(f"[PLANNER] Files to create: {len(plan.files_to_create)}")
                            break
                        except Exception as e:
                            logger.error(f"[PLANNER] Failed to parse PlannerResponse: {e}")
                            logger.error(f"[PLANNER] Args were: {args}")
                
                if plan:
                    break
        
        # Если PlannerResponse не найден, пробуем fallback на JSON парсинг
        if plan is None:
            logger.warning("[PLANNER] PlannerResponse tool not called, trying JSON fallback...")
            plan = _extract_plan_from_text(messages)
        
        if plan is None:
            logger.error("[PLANNER] Failed to extract plan!")
            # Создаём пустой план с ошибкой
            plan = PlannerResponse(
                component_name="Error",
                interface_name="IEcoError",
                methods=[],
                dependencies=[],
                files_to_create=[]
            )
        
        logger.info(f"[PLANNER] Done. Plan ready: {plan.component_name}")
        
        return {
            "plan": plan,
            "planner_messages": messages
        }
    
    return planner_node


def _extract_plan_from_text(messages) -> Optional[PlannerResponse]:
    """Fallback: извлекает план из текста сообщений (если tool не был вызван)."""
    
    all_content = ""
    for msg in messages:
        if hasattr(msg, 'content'):
            if isinstance(msg.content, str):
                all_content += msg.content + "\n"
            elif isinstance(msg.content, list):
                for item in msg.content:
                    if isinstance(item, str):
                        all_content += item
                    elif isinstance(item, dict) and 'text' in item:
                        all_content += item['text']
    
    if not all_content:
        logger.error("[PLANNER FALLBACK] No content in messages")
        return None
    
    logger.info(f"[PLANNER FALLBACK] Trying to parse JSON from {len(all_content)} chars")
    
    try:
        # Ищем JSON блок
        json_str = ""
        if "```json" in all_content:
            json_str = all_content.split("```json")[1].split("```")[0]
        elif "{" in all_content:
            start = all_content.find("{")
            end = all_content.rfind("}") + 1
            if start != -1 and end > start:
                json_str = all_content[start:end]
        
        if json_str:
            json_str = json_str.strip()
            data = json.loads(json_str)
            
            # Конвертируем methods если нужно
            methods = []
            for m in data.get('methods', []):
                if isinstance(m, dict):
                    methods.append(MethodDefinition(**m))
            
            return PlannerResponse(
                component_name=data.get('component_name', 'Unknown'),
                interface_name=data.get('interface_name', 'IEcoUnknown'),
                methods=methods,
                dependencies=data.get('dependencies', []),
                files_to_create=data.get('files_to_create', [])
            )
    except Exception as e:
        logger.error(f"[PLANNER FALLBACK] JSON parse failed: {e}")
    
    return None


# ═══════════════════════════════════════════════════════════════════════════
# HELPER: PARSE ERROR FILE
# ═══════════════════════════════════════════════════════════════════════════

def _extract_error_file(error_message: str) -> Optional[str]:
    """Извлекает путь к файлу из сообщения об ошибке MSBuild."""
    import re
    
    # Паттерны для извлечения файла из ошибок MSBuild/MSVC
    # Пример: H:\...\SourceFiles\CEcoCalc.c(35,5): error C2061
    patterns = [
        r'([A-Za-z]:\\[^\(]+)\(\d+,\d+\)',  # Windows path с (line,col)
        r'([A-Za-z]:\\[^\:]+\.(?:c|h))',     # Windows path .c или .h
        r'\.\.\\\.\.\\\.\.\\(\w+Files\\[^\s]+)',  # Relative path
    ]
    
    for pattern in patterns:
        match = re.search(pattern, error_message)
        if match:
            return match.group(1)
    
    return None


# ═══════════════════════════════════════════════════════════════════════════
# BUILDER NODE (с structured output через tool)
# ═══════════════════════════════════════════════════════════════════════════

def create_builder_node(llm):
    """
    Создаёт Builder как ReAct агент со structured output.
    
    Использует BuilderResponse как tool для сигнализации готовности.
    """
    
    # Добавляем BuilderResponse как tool
    builder_tools_with_response = BUILDER_TOOLS + [BuilderResponse]
    
    # Создаём ReAct агент
    # НЕ используем tool_choice - он конфликтует с create_react_agent
    builder_agent = create_react_agent(
        llm,
        tools=builder_tools_with_response,
        prompt=BUILDER_SYSTEM_PROMPT
    )
    
    def builder_node(state: AgentStateV2) -> Dict[str, Any]:
        logger.info("=" * 60)
        logger.info("[BUILDER] Starting...")
        
        plan = state.get("plan")
        error_message = state.get("error_message", "")
        context_summary = state.get("builder_context_summary", "")
        files_created = state.get("files_created", [])
        iteration = state.get("iteration", 0)
        
        if plan is None:
            logger.error("[BUILDER] No plan received!")
            return {
                "files_created": [],
                "builder_response": None,
                "builder_messages": [],
                "builder_context_summary": "",
                "error_message": "No plan from Planner"
            }
        
        # Конвертируем PlannerResponse в dict для промпта
        if isinstance(plan, PlannerResponse):
            plan_dict = plan.model_dump()
        else:
            plan_dict = plan
        
        # Формируем промпт в зависимости от итерации
        if error_message and iteration > 0:
            # RETRY: используем сжатый контекст + ошибку
            logger.info(f"[BUILDER] RETRY iteration {iteration}")
            logger.info(f"[BUILDER] Using summarized context ({len(context_summary)} chars)")
            
            # Парсим ошибку чтобы найти файл
            error_file = _extract_error_file(error_message)
            
            prompt = f"""ИСПРАВЛЕНИЕ ОШИБКИ КОМПИЛЯЦИИ (попытка {iteration + 1})

══════════════════════════════════════════════════════════════
ЧТО БЫЛО СДЕЛАНО РАНЕЕ:
══════════════════════════════════════════════════════════════
{context_summary}

Созданные файлы: {', '.join(files_created)}

══════════════════════════════════════════════════════════════
ОШИБКА КОМПИЛЯЦИИ:
══════════════════════════════════════════════════════════════
{error_message[:1500]}

══════════════════════════════════════════════════════════════
ТВОЯ ЗАДАЧА:
══════════════════════════════════════════════════════════════
1. Проанализируй ошибку
2. Найди файл с ошибкой{f': {error_file}' if error_file else ''}
3. Прочитай пример из source/Lessons/ если нужно
4. Исправь файл через write_file()
5. Вызови build("{plan_dict.get('component_name', 'Unknown')}") снова
6. Если успех - вызови BuilderResponse tool

ТИПИЧНЫЕ РЕШЕНИЯ:
- "IEcoMemoryAllocator1 undeclared" → добавь #include "IdEcoMemoryManager1.h"
- "IEcoSystem1.h not found" → проверь include path
- "syntax error" → проверь структуру и скобки"""
        else:
            # ПЕРВЫЙ ЗАПУСК: полный промпт
            logger.info("[BUILDER] First run - full prompt")
            prompt = get_builder_prompt(plan_dict)
        
        files_count = len(plan_dict.get('files_to_create', []))
        logger.info(f"[BUILDER] Plan has {files_count} files to create")
        logger.info(f"[BUILDER] Tools: {[t.name if hasattr(t, 'name') else t.__name__ for t in builder_tools_with_response]}")
        
        # Запускаем агент с БОЛЬШИМ лимитом шагов
        # Для каждого файла: read_file (пример) + write_file = 2 шага минимум
        # 8 файлов = 16 шагов + list_files + BuilderResponse = ~25-30 шагов
        result = builder_agent.invoke(
            {"messages": [("user", prompt)]},
            {"recursion_limit": 100}  # Достаточно для создания всех файлов
        )
        
        messages = result.get("messages", [])
        logger.info(f"[BUILDER] Got {len(messages)} messages from agent")
        
        # Собираем файлы из ToolMessage результатов write_file
        files_created = []
        builder_response = None
        
        for msg in messages:
            msg_type = type(msg).__name__
            
            # Проверяем ToolMessage с результатом write_file
            if msg_type == 'ToolMessage':
                content = str(msg.content) if hasattr(msg, 'content') else ""
                if "OK: Файл записан:" in content:
                    path = content.split("OK: Файл записан:")[-1].strip()
                    files_created.append(path)
                    logger.info(f"[BUILDER] File created: {path}")
            
            # Проверяем tool_calls для BuilderResponse
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.get('name', '')
                    
                    if tool_name == 'BuilderResponse':
                        args = tool_call.get('args', {})
                        logger.info(f"[BUILDER] BuilderResponse called!")
                        try:
                            builder_response = BuilderResponse(**args)
                            logger.info(f"[BUILDER] Project: {builder_response.project_name}")
                            logger.info(f"[BUILDER] Ready for build: {builder_response.ready_for_build}")
                        except Exception as e:
                            logger.error(f"[BUILDER] Failed to parse BuilderResponse: {e}")
        
        # Объединяем с предыдущими файлами (для retry)
        all_files_created = list(set(state.get("files_created", []) + files_created))
        
        logger.info(f"[BUILDER] Done. Files created this run: {len(files_created)}")
        logger.info(f"[BUILDER] Total files: {len(all_files_created)}")
        for f in files_created:
            logger.info(f"[BUILDER]   - {f}")
        
        return {
            "files_created": all_files_created,
            "builder_response": builder_response,
            "builder_messages": messages,
            "builder_context_summary": "",  # Очищаем после использования
            "error_message": ""  # Сбрасываем ошибку
        }
    
    return builder_node


# ═══════════════════════════════════════════════════════════════════════════
# QA NODE (BUILD + SUMMARIZE)
# ═══════════════════════════════════════════════════════════════════════════

def create_qa_node(llm):
    """
    Создаёт QA ноду с доступом к LLM для сжатия контекста.
    
    QA нода:
    1. Вызывает build
    2. При ошибке - сжимает контекст Builder через LLM
    3. Возвращает summary + error для retry
    """
    
    def qa_node(state: AgentStateV2) -> Dict[str, Any]:
        """QA нода - собирает проект и сжимает контекст при ошибке."""
        
        logger.info("=" * 60)
        logger.info("[QA] Starting build...")
        
        plan = state.get("plan")
        builder_response = state.get("builder_response")
        files_created = state.get("files_created", [])
        builder_messages = state.get("builder_messages", [])
        iteration = state.get("iteration", 0) + 1
        
        # Извлекаем имя проекта
        if builder_response and builder_response.project_name:
            project_name = builder_response.project_name
        elif isinstance(plan, PlannerResponse):
            project_name = f"Eco.{plan.component_name}"
        elif isinstance(plan, dict):
            project_name = f"Eco.{plan.get('component_name', 'Unknown')}"
        else:
            project_name = "Eco.Unknown"
        
        logger.info(f"[QA] Project: {project_name}")
        logger.info(f"[QA] Files created: {len(files_created)}")
        logger.info(f"[QA] Iteration: {iteration}")
        
        # Проверяем что файлы созданы
        if isinstance(plan, PlannerResponse):
            expected_files = plan.files_to_create
        elif isinstance(plan, dict):
            expected_files = plan.get("files_to_create", [])
        else:
            expected_files = []
        
        if len(files_created) < len(expected_files):
            missing = len(expected_files) - len(files_created)
            logger.warning(f"[QA] Missing {missing} files")
            for f in expected_files:
                if f not in files_created:
                    logger.warning(f"[QA]   Missing: {f}")
        
        # Запускаем сборку
        logger.info(f"[QA] Starting build for: {project_name}")
        build_result = build.invoke({"project_name": project_name})
        
        logger.info(f"[QA] Build result: {build_result[:300]}...")
        
        is_success = build_result.startswith("OK:")
        
        # Результат
        result = {
            "build_result": build_result,
            "is_success": is_success,
            "iteration": iteration
        }
        
        if is_success:
            logger.info("[QA] BUILD SUCCESS!")
            result["error_message"] = ""
            result["builder_context_summary"] = ""
        else:
            logger.error("[QA] BUILD FAILED - summarizing context for retry...")
            
            # Сжимаем контекст Builder для retry
            summary = summarize_builder_context(llm, builder_messages, files_created)
            
            logger.info(f"[QA] Context summary: {summary[:200]}...")
            
            result["error_message"] = build_result
            result["builder_context_summary"] = summary
            
            # Очищаем builder_messages для следующей итерации (экономим токены)
            result["builder_messages"] = []
        
        return result
    
    return qa_node


# ═══════════════════════════════════════════════════════════════════════════
# ROUTING
# ═══════════════════════════════════════════════════════════════════════════

def should_retry(state: AgentStateV2) -> Literal["builder", "end"]:
    """Определяет, нужно ли повторить сборку."""
    
    is_success = state.get("is_success", False)
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 3)
    
    if is_success:
        logger.info("[ROUTER] Build successful, finishing")
        return "end"
    
    if iteration >= max_iterations:
        logger.info(f"[ROUTER] Max iterations ({max_iterations}) reached, finishing")
        return "end"
    
    logger.info(f"[ROUTER] Build failed, retrying (iteration {iteration}/{max_iterations})")
    return "builder"


# ═══════════════════════════════════════════════════════════════════════════
# GRAPH BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def create_agent_graph_v2(llm):
    """
    Создаёт граф агента v2.
    
    Архитектура:
        START → planner → builder → qa → (builder | END)
        
    При ошибке сборки:
        - QA сжимает контекст Builder через LLM
        - Builder получает summary + error для исправления
    """
    
    logger.info("[GRAPH] Creating agent graph v2...")
    
    graph_builder = StateGraph(AgentStateV2)
    
    # Добавляем ноды (QA теперь тоже factory с LLM)
    graph_builder.add_node("planner", create_planner_node(llm))
    graph_builder.add_node("builder", create_builder_node(llm))
    graph_builder.add_node("qa", create_qa_node(llm))
    
    # Добавляем рёбра
    graph_builder.add_edge(START, "planner")
    graph_builder.add_edge("planner", "builder")
    graph_builder.add_edge("builder", "qa")
    
    # Условный переход после QA
    graph_builder.add_conditional_edges(
        "qa",
        should_retry,
        {
            "builder": "builder",
            "end": END
        }
    )
    
    # Компилируем
    memory = MemorySaver()
    graph = graph_builder.compile(checkpointer=memory)
    
    logger.info("[GRAPH] Graph created successfully")
    
    return graph


# ═══════════════════════════════════════════════════════════════════════════
# RUN FUNCTION
# ═══════════════════════════════════════════════════════════════════════════

def run_agent(llm, user_request: str, max_iterations: int = 3) -> Dict[str, Any]:
    """
    Запускает агент для генерации компонента.
    
    Args:
        llm: Языковая модель
        user_request: Запрос пользователя
        max_iterations: Максимум итераций при ошибках
    
    Returns:
        Финальное состояние агента
    """
    
    logger.info("=" * 80)
    logger.info("[RUN] Starting agent run with structured output")
    logger.info(f"[RUN] Request: {user_request}")
    logger.info(f"[RUN] Max iterations: {max_iterations}")
    logger.info("=" * 80)
    
    graph = create_agent_graph_v2(llm)
    
    initial_state = {
        "user_request": user_request,
        "plan": None,  # PlannerResponse или None
        "planner_messages": [],
        "builder_response": None,  # BuilderResponse или None
        "files_created": [],
        "builder_messages": [],
        "builder_context_summary": "",  # Сжатый контекст для retry
        "build_result": "",
        "is_success": False,
        "error_message": "",
        "iteration": 0,
        "max_iterations": max_iterations
    }
    
    # Запускаем с thread_id для checkpointer
    import uuid
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    logger.info(f"[RUN] Thread ID: {thread_id}")
    
    try:
        final_state = graph.invoke(initial_state, config)
        
        logger.info("=" * 80)
        logger.info("[RUN] Agent run completed")
        
        # Логируем результат
        is_success = final_state.get('is_success', False)
        plan = final_state.get('plan')
        
        if is_success:
            logger.info("[RUN] ✓ SUCCESS!")
        else:
            logger.info("[RUN] ✗ FAILED")
        
        if isinstance(plan, PlannerResponse):
            logger.info(f"[RUN] Component: {plan.component_name}")
            logger.info(f"[RUN] Interface: {plan.interface_name}")
            logger.info(f"[RUN] Methods: {len(plan.methods)}")
        
        logger.info(f"[RUN] Files created: {len(final_state.get('files_created', []))}")
        logger.info(f"[RUN] Iterations: {final_state.get('iteration', 0)}")
        logger.info(f"[RUN] Build result: {final_state.get('build_result', 'N/A')[:200]}")
        logger.info("=" * 80)
        
        return final_state
        
    except Exception as e:
        logger.error(f"[RUN] Exception during agent run: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
