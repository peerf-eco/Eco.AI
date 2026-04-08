"""
Pre-build verification for EcoMain.c.

Pure Python, no LLM. Checks generated code against resolved component
metadata before sending it to compilation.
"""

import re
from typing import Any, Dict, List

from .header_parser import build_method_map


def verify_ecomain(
    ecomain_content: str,
    resolved_components: list,
    framework_components: list,
) -> List[Dict[str, str]]:
    """Verify EcoMain.c before compilation."""
    errors: List[Dict[str, str]] = []
    errors.extend(_check_includes(ecomain_content, resolved_components))
    errors.extend(_check_factory_declarations(ecomain_content, resolved_components))
    errors.extend(_check_framework_registration(ecomain_content, framework_components))
    errors.extend(_check_method_calls(ecomain_content, resolved_components))
    errors.extend(_check_vtbl_pattern(ecomain_content))
    errors.extend(_check_eco_os_macro(ecomain_content))
    return errors


def _check_includes(code: str, resolved_components: list) -> list:
    """
    Each resolved component must include both IEco*.h and IdEco*.h headers.
    """
    errors = []
    for comp in resolved_components:
        if comp.get("is_framework"):
            continue
        name = comp.get("name", "")

        for hname in comp.get("header_contents", {}):
            if hname.startswith("IEco") and hname.endswith(".h"):
                if f'#include "{hname}"' not in code:
                    errors.append(
                        {
                            "check": "missing_include",
                            "message": f'Missing #include "{hname}" for component {name}',
                            "severity": "error",
                        }
                    )

        for hname in comp.get("header_contents", {}):
            if hname.startswith("IdEco") and hname.endswith(".h"):
                if f'#include "{hname}"' not in code:
                    errors.append(
                        {
                            "check": "missing_id_include",
                            "message": f'Missing #include "{hname}" for component {name} (needed for CID)',
                            "severity": "error",
                        }
                    )

    return errors


def _check_factory_declarations(code: str, resolved_components: list) -> list:
    """
    Each ECO_LIB component should reference its factory declaration.
    """
    errors = []
    for comp in resolved_components:
        factory = comp.get("factory_func", "")
        if not factory:
            continue
        if factory not in code:
            errors.append(
                {
                    "check": "missing_factory",
                    "message": f"Factory function {factory} for {comp.get('name', '?')} not found in code",
                    "severity": "warning",
                }
            )
    return errors


def _check_framework_registration(code: str, framework_components: list) -> list:
    """
    InterfaceBus1 and FileSystemManagement1 must be registered before user components.
    """
    errors = []

    register_calls = [
        (match.start(), match.group(1))
        for match in re.finditer(r"RegisterComponent\s*\([^,]+,\s*&(\w+)", code)
    ]

    if not register_calls:
        return errors

    bus_pos = None
    fsm_pos = None
    first_user_pos = None

    for pos, cid_name in register_calls:
        if "InterfaceBus" in cid_name:
            bus_pos = pos
        elif "FileSystem" in cid_name:
            fsm_pos = pos
        elif "MemoryManager" not in cid_name and "System1" not in cid_name:
            if first_user_pos is None:
                first_user_pos = pos

    if first_user_pos is not None:
        if bus_pos is None:
            errors.append(
                {
                    "check": "missing_bus_registration",
                    "message": "InterfaceBus1 must be registered before user components",
                    "severity": "error",
                }
            )
        elif bus_pos > first_user_pos:
            errors.append(
                {
                    "check": "wrong_registration_order",
                    "message": "InterfaceBus1 registered AFTER user components - must be BEFORE",
                    "severity": "error",
                }
            )

        if fsm_pos is None:
            errors.append(
                {
                    "check": "missing_fsm_registration",
                    "message": "FileSystemManagement1 must be registered before user components",
                    "severity": "error",
                }
            )
        elif fsm_pos > first_user_pos:
            errors.append(
                {
                    "check": "wrong_registration_order",
                    "message": "FileSystemManagement1 registered AFTER user components - must be BEFORE",
                    "severity": "error",
                }
            )

    return errors


def _check_method_calls(code: str, resolved_components: list) -> list:
    """Verify that called methods exist in the interface VTbl."""
    errors = []
    method_map = build_method_map(resolved_components)

    call_pattern = re.compile(r"(\w+)->pVTbl->(\w+)\s*\(")

    for match in call_pattern.finditer(code):
        var_name = match.group(1)
        method_name = match.group(2)

        if method_name in (
            "QueryInterface",
            "AddRef",
            "Release",
            "QueryComponent",
            "RegisterComponent",
        ):
            continue

        var_decl = re.search(rf"(IEco\w+)\s*\*\s*{re.escape(var_name)}", code)
        if not var_decl:
            continue

        iface_name = var_decl.group(1)

        if iface_name in method_map:
            known_methods = {method["name"] for method in method_map[iface_name]}
            if method_name not in known_methods:
                errors.append(
                    {
                        "check": "unknown_method",
                        "message": (
                            f"Method '{method_name}' not found in {iface_name} VTbl. "
                            f"Available: {', '.join(sorted(known_methods))}"
                        ),
                        "severity": "error",
                    }
                )

    return errors


def _check_vtbl_pattern(code: str) -> list:
    """
    Verify calls go through pVTbl, not directly through the interface pointer.
    """
    errors = []

    direct_calls = re.finditer(
        r"(g_pI\w+)->(?!pVTbl)(\w+)\s*\(",
        code,
    )

    for match in direct_calls:
        var_name = match.group(1)
        method = match.group(2)
        errors.append(
            {
                "check": "missing_pvtbl",
                "message": f"Direct call {var_name}->{method}() - should be {var_name}->pVTbl->{method}()",
                "severity": "error",
            }
        )

    return errors


def _check_eco_os_macro(code: str) -> list:
    """ECO_OS must not be defined for Windows CRT builds."""
    errors = []
    if re.search(r"#\s*define\s+ECO_OS", code):
        errors.append(
            {
                "check": "eco_os_defined",
                "message": "#define ECO_OS found - this conflicts with CRT on Windows, remove it",
                "severity": "error",
            }
        )
    return errors
