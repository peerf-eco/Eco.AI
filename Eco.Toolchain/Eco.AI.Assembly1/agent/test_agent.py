"""
EcoOS Agent - Автотест

Запускает полный цикл агента и сохраняет результаты в файл.

Использование:
    python -m agent.test_agent
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


# ═══════════════════════════════════════════════════════════════════════════
# LOGGING SETUP
# ═══════════════════════════════════════════════════════════════════════════

def setup_logging(log_file: Path):
    """Настраивает логирование в файл и консоль."""
    
    # Создаём форматтер
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Консольный хендлер
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Файловый хендлер
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Настраиваем root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    return logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# TEST RUNNER
# ═══════════════════════════════════════════════════════════════════════════

def run_test(test_name: str, user_request: str, logger: logging.Logger) -> dict:
    """
    Запускает один тест.
    
    Args:
        test_name: Название теста
        user_request: Запрос пользователя
        logger: Логгер
    
    Returns:
        Результат теста
    """
    
    logger.info("=" * 80)
    logger.info(f"TEST: {test_name}")
    logger.info(f"REQUEST: {user_request}")
    logger.info("=" * 80)
    
    result = {
        "test_name": test_name,
        "user_request": user_request,
        "start_time": datetime.now().isoformat(),
        "success": False,
        "error": None,
        "plan": None,
        "builder_response": None,
        "files_created": [],
        "build_result": None,
        "iterations": 0
    }
    
    try:
        # Импортируем здесь чтобы логирование уже было настроено
        from langchain_openai import ChatOpenAI
        from agent.graph_v2 import run_agent_v3
        
        # Создаём LLM
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1")
        model = os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4")
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set in environment")
        
        logger.info(f"Using model: {model}")
        logger.info(f"Using base URL: {base_url}")
        
        llm = ChatOpenAI(
            model=model,
            openai_api_key=api_key,
            openai_api_base=base_url,
            temperature=0
        )
        
        # Запускаем агент
        final_state = run_agent_v3(llm, user_request, max_iterations=3)
        
        # Заполняем результат
        result["success"] = final_state.get("is_success", False)
        
        # Plan может быть PlannerResponse (Pydantic) или dict
        plan = final_state.get("plan")
        if plan is not None:
            if hasattr(plan, 'model_dump'):
                # Pydantic модель - конвертируем в dict
                result["plan"] = plan.model_dump()
            else:
                result["plan"] = plan
        else:
            result["plan"] = {}
        
        # Builder response
        builder_response = final_state.get("builder_response")
        if builder_response is not None and hasattr(builder_response, 'model_dump'):
            result["builder_response"] = builder_response.model_dump()
        else:
            result["builder_response"] = None
        
        result["files_created"] = final_state.get("files_created", [])
        result["build_result"] = final_state.get("build_result", "")
        result["iterations"] = final_state.get("iteration", 0)
        
        if not result["success"]:
            result["error"] = final_state.get("error_message", "Unknown error")
        
    except Exception as e:
        logger.exception(f"Test failed with exception: {e}")
        result["error"] = str(e)
    
    result["end_time"] = datetime.now().isoformat()
    
    # Логируем результат
    logger.info("-" * 80)
    logger.info(f"TEST RESULT: {'PASSED' if result['success'] else 'FAILED'}")
    logger.info(f"Files created: {len(result['files_created'])}")
    logger.info(f"Iterations: {result['iterations']}")
    if result["error"]:
        logger.error(f"Error: {result['error'][:500]}")
    logger.info("-" * 80)
    
    return result


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Главная функция автотеста."""
    
    # Создаём директорию для результатов
    results_dir = Path(__file__).parent.parent / "test_results"
    results_dir.mkdir(exist_ok=True)
    
    # Имя файла с timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = results_dir / f"test_run_{timestamp}.log"
    results_file = results_dir / f"test_results_{timestamp}.json"
    
    # Настраиваем логирование
    logger = setup_logging(log_file)
    
    logger.info("=" * 80)
    logger.info("ECOOS AGENT AUTOTEST")
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"Results file: {results_file}")
    logger.info("=" * 80)
    
    # Список тестов
    tests = [
        {
            "name": "simple_calculator",
            "request": "Создай простой калькулятор с операцией сложения двух целых чисел"
        },
        # Можно добавить больше тестов:
        # {
        #     "name": "calculator_with_logging",
        #     "request": "Создай калькулятор с + и - с логированием операций"
        # },
    ]
    
    # Запускаем тесты
    all_results = {
        "run_timestamp": timestamp,
        "log_file": str(log_file),
        "tests": []
    }
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = run_test(test["name"], test["request"], logger)
            all_results["tests"].append(result)
            
            if result["success"]:
                passed += 1
            else:
                failed += 1
                
        except Exception as e:
            logger.exception(f"Critical error in test {test['name']}: {e}")
            all_results["tests"].append({
                "test_name": test["name"],
                "error": str(e),
                "success": False
            })
            failed += 1
    
    # Итоги
    all_results["summary"] = {
        "total": len(tests),
        "passed": passed,
        "failed": failed
    }
    
    # Сохраняем результаты
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    logger.info("=" * 80)
    logger.info("AUTOTEST COMPLETED")
    logger.info(f"Total: {len(tests)}, Passed: {passed}, Failed: {failed}")
    logger.info(f"Results saved to: {results_file}")
    logger.info("=" * 80)
    
    # Выводим краткий отчёт
    print("\n" + "=" * 60)
    print("AUTOTEST SUMMARY")
    print("=" * 60)
    print(f"Total tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"\nLog file: {log_file}")
    print(f"Results: {results_file}")
    print("=" * 60)
    
    # Возвращаем код выхода
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
