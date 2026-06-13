"""
EcoOS Component Agent - Entry Point

Точка входа для запуска агента.

Использование:
    python -m agent.main "Создай калькулятор с логированием"
    
Или в интерактивном режиме:
    python -m agent.main --interactive
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()


def get_llm():
    """
    Инициализирует LLM модель с поддержкой OpenRouter (langchain ChatOpenAI).

    Используется legacy V5/V6 endpoints. Новый код должен использовать
    get_model() — pi_ai.Model, без langchain.
    """
    from langchain_openai import ChatOpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1")
    model = os.getenv("LLM_MODEL", "moonshotai/kimi-k2-thinking")

    if not api_key:
        print("[ERROR] OPENAI_API_KEY not set")
        print("[INFO] Set it in .env file or export OPENAI_API_KEY=your-key")
        sys.exit(1)

    print(f"[INFO] Using LLM: {model}")
    print(f"[INFO] API URL: {base_url}")

    return ChatOpenAI(
        model=model,
        temperature=0,
        openai_api_key=api_key,
        openai_api_base=base_url,
        timeout=30,
        max_retries=2,
    )


def get_model():
    """Build a pi_ai.Model for the configured OpenRouter endpoint.

    Used by V7 endpoint (and any new code) instead of get_llm(). The model
    streams via pi_ai.stream_simple, which passes delta.reasoning through
    correctly (langchain_openai 1.2.1 silently drops that field).
    """
    from agent.pi_ai import Model, ModelCost, OpenAICompletionsCompat, OpenRouterRouting

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1")
    model_id = os.getenv("LLM_MODEL", "moonshotai/kimi-k2-thinking")

    if not api_key:
        print("[ERROR] OPENAI_API_KEY not set")
        print("[INFO] Set it in .env file or export OPENAI_API_KEY=your-key")
        sys.exit(1)

    # Implicit prompt cache lives per upstream provider; OpenRouter's default
    # load-balancing hops between providers and zeroes the hit-rate. Pinning
    # one provider keeps the prefix cache warm across agent-loop iterations
    # (measured 2026-06-12: cached=99.6%, -81% per-call cost on z-ai/glm-5.1).
    routing = None
    pin = os.getenv("OPENROUTER_PROVIDER_PIN", "").strip()
    if pin:
        routing = OpenRouterRouting(
            order=[p.strip() for p in pin.split(",") if p.strip()],
            allow_fallbacks=False,
        )
        print(f"[INFO] OpenRouter provider pin: {pin} (fallbacks off)")

    print(f"[INFO] Using pi_ai Model: {model_id}")
    print(f"[INFO] API URL: {base_url}")

    return Model(
        id=model_id,
        name=model_id,
        api="openai-completions",
        provider="openrouter",
        baseUrl=base_url.rstrip("/"),
        reasoning=True,
        cost=ModelCost(),
        headers={"Authorization": f"Bearer {api_key}"},
        compat=OpenAICompletionsCompat(
            thinkingFormat="openrouter",
            openRouterRouting=routing,
        ),
    )


def main():
    parser = argparse.ArgumentParser(
        description="EcoOS Component Agent - генерация компонентов из кирпичиков"
    )
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="Запрос пользователя (что создать)"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Интерактивный режим (прямой V3 pipeline)"
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Chat mode — общение с агентом, сборка по запросу"
    )
    parser.add_argument(
        "--model",
        default=os.getenv("LLM_MODEL", "moonshotai/kimi-k2-thinking"),
        help=f"Модель LLM (default: {os.getenv('LLM_MODEL', 'moonshotai/kimi-k2-thinking')})"
    )
    parser.add_argument(
        "--output", "-o",
        default="./output",
        help="Директория для сгенерированных файлов"
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=int(os.getenv("AGENT_MAX_ITERATIONS", "10")),
        help=f"Максимум итераций перегенерации (default: {os.getenv('AGENT_MAX_ITERATIONS', '10')})"
    )
    args = parser.parse_args()
    
    # Переопределяем модель если указана в аргументах
    if args.model:
        os.environ["LLM_MODEL"] = args.model
    
    # ═══════════════════════════════════════════════════════════════════════
    # ИНИЦИАЛИЗАЦИЯ
    # ═══════════════════════════════════════════════════════════════════════
    
    from .graph_v2 import create_agent_graph_v3

    print("=" * 60)
    print("  EcoOS Component Agent V3")
    print("  Сборка приложений из SDK-компонентов EcoOS")
    print("=" * 60)
    print()

    llm = get_llm()
    graph = create_agent_graph_v3(llm)
    print("[INFO] Using V3 assembly graph (planner -> resolver -> writer -> build -> tester)")
    print()
    
    # ═══════════════════════════════════════════════════════════════════════
    # ЗАПУСК
    # ═══════════════════════════════════════════════════════════════════════
    
    if args.chat:
        from .chat_agent import create_chat_agent
        chat = create_chat_agent(llm)
        run_chat_mode(chat, llm, args)
    elif args.interactive:
        run_interactive(graph, args)
    elif args.query:
        run_single_query(graph, args.query, args)
    else:
        parser.print_help()
        sys.exit(1)


def run_single_query(graph, query: str, args):
    """Выполнить один запрос через V3 pipeline"""
    import uuid

    from .state_helpers import make_initial_v3_state

    print(f"[QUERY] {query}")
    print()

    initial_state = make_initial_v3_state(query, args.max_iterations)

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    print("[RUNNING] Processing request...")
    print()

    try:
        result = graph.invoke(initial_state, config=config)
    except Exception as e:
        print(f"[ERROR] Agent failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print_results(result, args)


def print_results(result: dict, args):
    """Выводит результаты V3 агента"""

    print()
    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)

    is_success = result.get("is_success", False)
    print(f"\n[Status] {'SUCCESS' if is_success else 'FAILED'}")

    # Component plan
    plan = result.get("component_plan", {})
    components = plan.get("components", [])
    print(f"[App] {plan.get('app_description', 'N/A')}")
    print(f"[Project] {plan.get('project_name', 'N/A')}")
    print(f"[Components] {len(components)} found:")
    for comp in components:
        print(f"  - {comp.get('name', '?')} ({comp.get('reason', '')})")

    # Build result
    build_result = result.get("build_result", "")
    if build_result:
        print(f"\n[Build] {build_result[:200]}")

    # Test results
    tests_passed = result.get("tests_passed", False)
    test_results = result.get("test_results", "")
    if test_results:
        print(f"\n[Tests] {'PASSED' if tests_passed else 'FAILED'}")
        print(test_results[:500])

    # Project directory
    project_dir = result.get("project_dir", "")
    if project_dir:
        print(f"\n[Output] {project_dir}")

    print(f"[Iterations] {result.get('iteration', 0)}")

    if not is_success:
        error = result.get("error_message", "")
        if error:
            print(f"\n[Error] {error[:500]}")

    print()


def run_interactive(graph, args):
    """Интерактивный режим"""
    
    print("[MODE] Interactive mode")
    print("Type your request or 'quit' to exit")
    print()
    
    while True:
        try:
            query = input(">>> ").strip()
            
            if not query:
                continue
            
            if query.lower() in ('quit', 'exit', 'q'):
                print("Goodbye!")
                break
            
            run_single_query(graph, query, args)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break


def run_chat_mode(chat_agent, llm, args):
    """Chat mode — conversation with agent, assembly only on request."""
    from .chat_agent import ChatContext

    print("[MODE] Chat mode — общайтесь с агентом или попросите собрать приложение")
    print("Type 'quit' to exit")
    print()

    thread_id = "cli-chat"
    config = {"configurable": {"thread_id": thread_id}}
    context = ChatContext(llm=llm, max_iterations=args.max_iterations)

    while True:
        try:
            query = input(">>> ").strip()
            if not query:
                continue
            if query.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break

            inputs = {"messages": [{"role": "user", "content": query}]}

            for chunk in chat_agent.stream(
                inputs,
                config=config,
                context=context,
                stream_mode=["messages", "custom"],
            ):
                mode, data = chunk
                if mode == "messages":
                    msg_chunk, metadata = data
                    if hasattr(msg_chunk, "content") and msg_chunk.content:
                        if metadata.get("langgraph_node") == "agent":
                            print(msg_chunk.content, end="", flush=True)
                elif mode == "custom":
                    event_type = data.get("type", "")
                    if event_type == "progress":
                        print(f"\n  [{data['stage']}] {data.get('status', '')}")
                    elif event_type == "result":
                        res = data["data"]
                        status = "SUCCESS" if res["is_success"] else "FAILED"
                        tests = "PASSED" if res.get("tests_passed") else "FAILED"
                        print(f"\n  [Build: {status}] [Tests: {tests}] [{res.get('iterations', 0)} iter.]")

            print()  # newline after response

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
