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
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()


def get_llm():
    """
    Инициализирует LLM модель с поддержкой OpenRouter.
    
    Returns:
        Инициализированная LLM модель
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
        help="Интерактивный режим"
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
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Использовать упрощённый граф (без цикла проверки)"
    )
    
    args = parser.parse_args()
    
    # Переопределяем модель если указана в аргументах
    if args.model:
        os.environ["LLM_MODEL"] = args.model
    
    # ═══════════════════════════════════════════════════════════════════════
    # ИНИЦИАЛИЗАЦИЯ
    # ═══════════════════════════════════════════════════════════════════════
    
    from .graph import create_agent_graph, create_simple_graph
    
    print("=" * 60)
    print("  EcoOS Component Agent")
    print("  Генерация компонентов из кирпичиков EcoOS SDK")
    print("=" * 60)
    print()
    
    llm = get_llm()
    
    if args.simple:
        graph = create_simple_graph(llm)
        print("[INFO] Using simple graph (no review loop)")
    else:
        graph = create_agent_graph(llm)
        print("[INFO] Using full graph with review loop")
    
    print()
    
    # ═══════════════════════════════════════════════════════════════════════
    # ЗАПУСК
    # ═══════════════════════════════════════════════════════════════════════
    
    if args.interactive:
        run_interactive(graph, args)
    elif args.query:
        run_single_query(graph, args.query, args)
    else:
        parser.print_help()
        sys.exit(1)


def run_single_query(graph, query: str, args):
    """Выполнить один запрос"""
    
    print(f"[QUERY] {query}")
    print()
    
    # Начальное состояние
    initial_state = {
        "messages": [{"role": "user", "content": query}],
        "max_iterations": args.max_iterations,
        "iteration_count": 0,
        "selected_components": [],
        "retrieved_headers": {},
        "retrieved_examples": {},
        "code_patterns": {},
        "generated_files": [],
        "validation_errors": [],
        "is_valid": False,
    }
    
    # Конфигурация для checkpointer
    config = {"configurable": {"thread_id": "main"}}
    
    # Запуск графа
    print("[RUNNING] Processing request...")
    print()
    
    try:
        result = graph.invoke(initial_state, config=config)
    except Exception as e:
        print(f"[ERROR] Agent failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # ═══════════════════════════════════════════════════════════════════════
    # ВЫВОД РЕЗУЛЬТАТОВ
    # ═══════════════════════════════════════════════════════════════════════
    
    print_results(result, args)


def print_results(result: dict, args):
    """Выводит результаты работы агента"""
    
    print()
    print("=" * 60)
    print("  RESULTS")
    print("=" * 60)
    
    print(f"\n[Intent] {result.get('user_intent', 'N/A')}")
    print(f"[Features] {result.get('required_features', [])}")
    print(f"[Platform] {result.get('target_platform', 'N/A')}")
    
    components = result.get('selected_components', [])
    print(f"\n[Components] {len(components)} selected:")
    for comp in components:
        cid = comp.get('cid', 'N/A')
        print(f"  - {comp['name']} ({cid[:8] if len(cid) > 8 else cid}...)")
    
    files = result.get('generated_files', [])
    print(f"\n[Generated Files] {len(files)} files:")
    
    # Создаём директорию для вывода
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for file in files:
        file_path = output_dir / file['path']
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file['content'])
        
        print(f"  [OK] {file['path']} ({file['file_type']})")
    
    # Ошибки валидации
    errors = result.get('validation_errors', [])
    if errors:
        print(f"\n[Validation] {len(errors)} issues:")
        for err in errors:
            severity = "[WARN]" if err['severity'] == 'warning' else "[ERROR]"
            print(f"  {severity} {err['file']}: {err['message']}")
    
    print(f"\n[Output] Files saved to: {output_dir.absolute()}")
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


if __name__ == "__main__":
    main()
