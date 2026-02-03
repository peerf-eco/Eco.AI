"""
EcoOS Component Agent - LangGraph Definition

Граф агента для генерации компонентов EcoOS.

Архитектура:
    ┌──────────┐     ┌──────────────┐     ┌─────────────┐     ┌────────────┐
    │  START   │────▶│ analyze_req  │────▶│ select_comp │────▶│ retrieve_  │
    └──────────┘     └──────────────┘     └─────────────┘     │  context   │
                                                               └─────┬──────┘
                                                                     │
    ┌──────────┐     ┌──────────────┐     ┌─────────────┐            │
    │   END    │◀────│   review     │◀────│  generate   │◀───────────┘
    └──────────┘     └──────────────┘     └─────────────┘
         ▲                  │                    ▲
         │                  │                    │
         │                  └────────────────────┘
         │                    (если ошибки)
         │
         └────────────────── (если OK) ────────────────────────────────
"""

from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from .state import AgentState
from .nodes.analyze import create_analyze_node
from .nodes.select import select_components
from .nodes.retrieve import retrieve_context
from .nodes.generate import create_generate_node
from .nodes.review import create_review_node


def should_regenerate(state: AgentState) -> Literal["generate", "end"]:
    """
    Определяет, нужно ли перегенерировать код.
    
    Логика:
    - Если код валиден → "end"
    - Если есть ошибки и не превышен лимит итераций → "generate"
    - Если превышен лимит → "end" (принимаем как есть)
    
    Args:
        state: Текущее состояние агента
        
    Returns:
        "generate" - для перегенерации
        "end" - для завершения
    """
    
    is_valid = state.get("is_valid", False)
    iteration_count = state.get("iteration_count", 0)
    max_iterations = state.get("max_iterations", 3)
    
    if is_valid:
        print(f"[ROUTER] Code is valid, finishing")
        return "end"
    
    if iteration_count >= max_iterations:
        print(f"[ROUTER] Max iterations reached ({iteration_count}/{max_iterations}), accepting code as-is")
        return "end"
    
    print(f"[ROUTER] Code has errors, regenerating (iteration {iteration_count}/{max_iterations})")
    return "generate"


# ═══════════════════════════════════════════════════════════════════════════
# СОЗДАНИЕ ГРАФОВ
# ═══════════════════════════════════════════════════════════════════════════


def create_agent_graph(llm):
    """
    Создаёт граф агента с привязанной LLM.
    
    Args:
        llm: Языковая модель (ChatOpenAI, ChatAnthropic, etc.)
        
    Returns:
        Скомпилированный граф
        
    Использование:
        from langchain_openai import ChatOpenAI
        
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        graph = create_agent_graph(llm)
        
        result = graph.invoke({
            "messages": [{"role": "user", "content": "Создай калькулятор с логированием"}],
            "max_iterations": 3,
            "iteration_count": 0,
        })
    """
    
    # ═══════════════════════════════════════════════════════════════════════
    # СОЗДАНИЕ ГРАФА
    # ═══════════════════════════════════════════════════════════════════════
    
    builder = StateGraph(AgentState)
    
    # ═══════════════════════════════════════════════════════════════════════
    # ДОБАВЛЕНИЕ УЗЛОВ
    # ═══════════════════════════════════════════════════════════════════════
    
    # Узел анализа запроса
    builder.add_node("analyze_request", create_analyze_node(llm))
    
    # Узел выбора компонентов
    builder.add_node("select_components", select_components)
    
    # Узел извлечения контекста (RAG)
    builder.add_node("retrieve_context", retrieve_context)
    
    # Узел генерации кода
    builder.add_node("generate_code", create_generate_node(llm))
    
    # Узел проверки кода
    builder.add_node("review_code", create_review_node(llm))
    
    # ═══════════════════════════════════════════════════════════════════════
    # ДОБАВЛЕНИЕ РЁБЕР (EDGES)
    # ═══════════════════════════════════════════════════════════════════════
    
    # START → analyze_request
    builder.add_edge(START, "analyze_request")
    
    # analyze_request → select_components
    builder.add_edge("analyze_request", "select_components")
    
    # select_components → retrieve_context
    builder.add_edge("select_components", "retrieve_context")
    
    # retrieve_context → generate_code
    builder.add_edge("retrieve_context", "generate_code")
    
    # generate_code → review_code
    builder.add_edge("generate_code", "review_code")
    
    # review_code → (generate_code | END) - условный переход
    builder.add_conditional_edges(
        "review_code",
        should_regenerate,
        {
            "generate": "generate_code",  # Перегенерация
            "end": END,                   # Завершение
        }
    )
    
    # ═══════════════════════════════════════════════════════════════════════
    # КОМПИЛЯЦИЯ ГРАФА
    # ═══════════════════════════════════════════════════════════════════════
    
    # Добавляем checkpointer для сохранения состояния
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)
    
    return graph


def create_simple_graph(llm):
    """
    Упрощённая версия графа БЕЗ цикла перегенерации.
    
    Полезно для отладки и тестирования.
    
    START → analyze → select → retrieve → generate → END
    """
    
    builder = StateGraph(AgentState)
    
    builder.add_node("analyze_request", create_analyze_node(llm))
    builder.add_node("select_components", select_components)
    builder.add_node("retrieve_context", retrieve_context)
    builder.add_node("generate_code", create_generate_node(llm))
    
    builder.add_edge(START, "analyze_request")
    builder.add_edge("analyze_request", "select_components")
    builder.add_edge("select_components", "retrieve_context")
    builder.add_edge("retrieve_context", "generate_code")
    builder.add_edge("generate_code", END)
    
    return builder.compile()

