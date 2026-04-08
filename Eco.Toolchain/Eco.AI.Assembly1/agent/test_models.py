"""
Comparative test: run V3 pipeline on 3 models with the same request.

Usage:
    python -m agent.test_models

Compares: minimax/minimax-m2.7, moonshotai/kimi-k2.5, z-ai/glm-5
Request: "Собери калькулятор с функциями pow и sqrt"
"""

import os
import sys
import time
import json
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

MODELS = [
    "minimax/minimax-m2.7",
    "moonshotai/kimi-k2.5",
    "z-ai/glm-5",
]

REQUEST = "Собери калькулятор с функциями pow и sqrt"
MAX_ITERATIONS = 5


def make_llm(model_name: str):
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model_name,
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_api_base=os.getenv("OPENROUTER_URL", "https://openrouter.ai/api/v1"),
    )


def run_one(model_name: str) -> dict:
    """Run V3 pipeline with a given model, return metrics."""
    from .graph_v2 import run_agent_v3

    print(f"\n{'='*70}")
    print(f"  MODEL: {model_name}")
    print(f"{'='*70}")

    llm = make_llm(model_name)

    t0 = time.time()
    try:
        state = run_agent_v3(llm, REQUEST, max_iterations=MAX_ITERATIONS)
        elapsed = time.time() - t0

        # Extract metrics
        is_success = state.get("is_success", False)
        tests_passed = state.get("tests_passed", False)
        iterations = state.get("iteration", 0)
        verification_errors = state.get("verification_errors", "")
        build_result = state.get("build_result", "")
        test_results = state.get("test_results", "")
        ecomain_len = len(state.get("ecomain_content", ""))
        components = [c.get("name", "?") for c in state.get("resolved_components", [])]

        result = {
            "model": model_name,
            "success": is_success,
            "tests_passed": tests_passed,
            "iterations": iterations,
            "time_sec": round(elapsed, 1),
            "ecomain_chars": ecomain_len,
            "components": components,
            "had_verification_errors": bool(verification_errors),
            "build_ok": build_result.startswith("OK:") if build_result else False,
            "error": None,
        }

        # Save EcoMain.c for comparison
        ecomain = state.get("ecomain_content", "")
        if ecomain:
            safe_name = model_name.replace("/", "_")
            out_dir = Path(__file__).parent.parent / "test_results"
            out_dir.mkdir(exist_ok=True)
            (out_dir / f"EcoMain_{safe_name}.c").write_text(ecomain, encoding="utf-8")
            if test_results:
                (out_dir / f"tests_{safe_name}.txt").write_text(test_results, encoding="utf-8")

    except Exception as e:
        elapsed = time.time() - t0
        result = {
            "model": model_name,
            "success": False,
            "tests_passed": False,
            "iterations": 0,
            "time_sec": round(elapsed, 1),
            "ecomain_chars": 0,
            "components": [],
            "had_verification_errors": False,
            "build_ok": False,
            "error": str(e)[:200],
        }

    return result


def print_comparison(results: list):
    """Print side-by-side comparison table."""
    print(f"\n{'='*70}")
    print(f"  COMPARISON: {REQUEST}")
    print(f"{'='*70}\n")

    header = f"{'Metric':<30}"
    for r in results:
        short = r["model"].split("/")[-1][:15]
        header += f" {short:>15}"
    print(header)
    print("-" * len(header))

    rows = [
        ("Build success", "success"),
        ("Tests passed", "tests_passed"),
        ("Iterations", "iterations"),
        ("Time (sec)", "time_sec"),
        ("EcoMain.c chars", "ecomain_chars"),
        ("Had verif. errors", "had_verification_errors"),
        ("Build OK", "build_ok"),
    ]

    for label, key in rows:
        row = f"{label:<30}"
        for r in results:
            val = r.get(key, "N/A")
            if isinstance(val, bool):
                val = "YES" if val else "NO"
            row += f" {str(val):>15}"
        print(row)

    # Components
    print(f"\n{'Components found:':<30}")
    for r in results:
        short = r["model"].split("/")[-1][:15]
        comps = ", ".join(r.get("components", [])) or "none"
        print(f"  {short}: {comps}")

    # Errors
    for r in results:
        if r.get("error"):
            short = r["model"].split("/")[-1]
            print(f"\n  ERROR [{short}]: {r['error']}")

    # Save JSON
    out_dir = Path(__file__).parent.parent / "test_results"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "model_comparison.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nResults saved to test_results/model_comparison.json")


def main():
    logging.basicConfig(level=logging.WARNING)

    # Suppress verbose logging from agent
    for name in ["agent", "httpx", "openai", "langchain", "langgraph"]:
        logging.getLogger(name).setLevel(logging.WARNING)

    results = []
    for model in MODELS:
        r = run_one(model)
        results.append(r)

        # Quick status
        status = "OK" if r["success"] else "FAIL"
        tests = "PASS" if r["tests_passed"] else "FAIL"
        print(f"\n>>> {model}: build={status}, tests={tests}, "
              f"iters={r['iterations']}, time={r['time_sec']}s")

    print_comparison(results)


if __name__ == "__main__":
    main()
