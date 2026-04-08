"""
EcoOS Agent — State Helpers

Utility functions for creating initial state dicts.
"""


def make_initial_v3_state(user_request: str, max_iterations: int = 5) -> dict:
    """Create a fresh AgentStateV3-compatible dict for a new pipeline run."""
    return {
        "user_request": user_request,
        "component_plan": {},
        "planner_messages": [],
        "resolved_components": [],
        "framework_components": [],
        "include_dirs": [],
        "lib_dirs": [],
        "lib_files": [],
        "makefile_content": "",
        "makefile_exe_content": "",
        "project_dir": "",
        "missing_components": [],
        "build_platform": "",
        "ecomain_content": "",
        "writer_messages": [],
        "verification_errors": "",
        "build_result": "",
        "is_success": False,
        "error_message": "",
        "error_type": "none",
        "test_cases": "",
        "test_results": "",
        "tests_passed": False,
        "iteration": 0,
        "max_iterations": max_iterations,
    }
