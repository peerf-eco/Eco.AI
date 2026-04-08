"""
VTbl parser for EcoOS SDK headers.

Extracts a structured method map from IEco*.h headers for:
1. Writer prompt API reference
2. Pre-build EcoMain.c verification
"""

import re
from typing import Dict, List


VTBL_METHOD_RE = re.compile(
    r"^\s*"
    r"(?P<return_type>[\w\s\*]+?)\s*"
    r"\(\s*ECOCALLMETHOD\s*\*\s*"
    r"(?P<method_name>\w+)\s*\)"
    r"\s*\((?P<params>[^)]*)\)\s*;",
    re.MULTILINE,
)

BASE_METHODS = {"QueryInterface", "AddRef", "Release"}


def parse_vtbl_methods(header_content: str) -> List[Dict[str, str]]:
    """Extract VTbl methods from a single IEco*.h header."""
    methods: List[Dict[str, str]] = []
    for match in VTBL_METHOD_RE.finditer(header_content):
        name = match.group("method_name").strip()
        if name in BASE_METHODS:
            continue

        ret = match.group("return_type").strip()
        params = match.group("params").strip()

        methods.append(
            {
                "name": name,
                "return_type": ret,
                "params": params,
                "signature": f"{ret} {name}({params})",
            }
        )

    return methods


def build_method_map(resolved_components: list) -> Dict[str, List[Dict[str, str]]]:
    """Build interface_name -> methods map from resolved component headers."""
    method_map: Dict[str, List[Dict[str, str]]] = {}

    for comp in resolved_components:
        interface_name = comp.get("interface_name", "")
        if not interface_name:
            continue

        header_contents = comp.get("header_contents", {})

        for hname, hcontent in header_contents.items():
            if hname.startswith("IEco") and hname.endswith(".h"):
                methods = parse_vtbl_methods(hcontent)
                if methods:
                    method_map[interface_name] = methods
                    break

    return method_map


def format_method_map_for_prompt(method_map: Dict[str, List[Dict[str, str]]]) -> str:
    """Format the method map into a compact prompt-friendly API reference."""
    parts = []
    for iface, methods in method_map.items():
        parts.append(f"## {iface} - available methods")
        for method in methods:
            parts.append(f"  - {method['signature']}")
        parts.append("")

    return "\n".join(parts)
