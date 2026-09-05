import re
from typing import Any, Dict, List


class HybridRegexTool:
    # Python patterns
    PYTHON_FUNCTION_RE = re.compile(
        r"^\s*(async\s+def|def)\s+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*(?:->\s*([^:\n]+))?\s*:",
        re.MULTILINE,
    )
    PYTHON_CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_]\w*)\s*(?:\(([^)]*)\))?\s*:", re.MULTILINE)
    PYTHON_IMPORT_RE = re.compile(r"^\s*(?:from\s+([.\w]+)\s+import\s+([^\n#]+)|import\s+([^\n#]+))", re.MULTILINE)

    # JavaScript/TypeScript patterns
    JS_FUNCTION_RE = re.compile(
        r"^\s*(?:async\s+)?(?:function\s+([A-Za-z_$]\w*)\s*\(([^)]*)\)|const\s+([A-Za-z_$]\w*)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*=>|([A-Za-z_$]\w*)\s*:\s*(?:async\s+)?function\s*\(([^)]*)\))",
        re.MULTILINE,
    )
    JS_CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_$]\w*)(?:\s+extends\s+([A-Za-z_$]\w*))?\s*{", re.MULTILINE)
    JS_IMPORT_RE = re.compile(r'^\s*import\s+.*from\s+["\']([^"\']+)["\']', re.MULTILINE)
    JS_VAR_RE = re.compile(r"^\s*(?:const|let|var)\s+([A-Za-z_$]\w*)", re.MULTILINE)

    # Java patterns
    JAVA_CLASS_RE = re.compile(r"^\s*(?:public\s+|private\s+|protected\s+)?(?:abstract\s+|final\s+)?class\s+([A-Za-z_$]\w*)(?:\s+extends\s+([A-Za-z_$]\w*))?(?:\s+implements\s+([^{]+))?\s*{", re.MULTILINE)
    JAVA_METHOD_RE = re.compile(r"^\s*(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:final\s+)?(?:abstract\s+)?(?:[A-Za-z_$]\w*\s+)*([A-Za-z_$]\w*)\s*\(([^)]*)\)\s*(?:throws\s+[^{]+)?\s*[{;]", re.MULTILINE)
    JAVA_IMPORT_RE = re.compile(r"^\s*import\s+(?:static\s+)?([^;]+);", re.MULTILINE)

    # C/C++ patterns
    C_FUNCTION_RE = re.compile(r"^\s*(?:[A-Za-z_][A-Za-z0-9_\s\*]*\s+)+([A-Za-z_]\w*)\s*\(([^)]*)\)\s*[{;]", re.MULTILINE)
    C_INCLUDE_RE = re.compile(r"^\s*#include\s*[<\"]([^>\"]+)[>\"]", re.MULTILINE)

    def extract(self, code: str) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []
        class_regions = self._class_regions(code)
        entities.extend(self._extract_imports(code))
        entities.extend(self._extract_classes(code))
        entities.extend(self._extract_functions_and_methods(code, class_regions))
        entities.extend(self._extract_variables(code))
        return entities

    def _extract_imports(self, code: str) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []

        # Python imports
        for m in self.PYTHON_IMPORT_RE.finditer(code):
            line = code.count("\n", 0, m.start()) + 1
            if m.group(1) and m.group(2):
                module = m.group(1).strip()
                names = [x.strip() for x in m.group(2).split(",")]
                for name in names:
                    name_clean = name.split(" as ")[0].strip()
                    entities.append({"type": "IMPORT", "name": f"{module}.{name_clean}", "line": line})
            else:
                names = [x.strip() for x in (m.group(3) or "").split(",")]
                for name in names:
                    name_clean = name.split(" as ")[0].strip()
                    if name_clean:
                        entities.append({"type": "IMPORT", "name": name_clean, "line": line})

        # JavaScript imports
        for m in self.JS_IMPORT_RE.finditer(code):
            line = code.count("\n", 0, m.start()) + 1
            module = m.group(1).strip()
            entities.append({"type": "IMPORT", "name": module, "line": line})

        # Java imports
        for m in self.JAVA_IMPORT_RE.finditer(code):
            line = code.count("\n", 0, m.start()) + 1
            import_name = m.group(1).strip().rstrip(";")
            entities.append({"type": "IMPORT", "name": import_name, "line": line})

        # C/C++ includes
        for m in self.C_INCLUDE_RE.finditer(code):
            line = code.count("\n", 0, m.start()) + 1
            include_name = m.group(1).strip()
            entities.append({"type": "IMPORT", "name": include_name, "line": line})

        return entities

    def _extract_classes(self, code: str) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []

        # Python classes
        for m in self.PYTHON_CLASS_RE.finditer(code):
            entities.append(
                {"type": "CLASS", "name": m.group(1), "line": code.count("\n", 0, m.start()) + 1}
            )

        # JavaScript/TypeScript classes
        for m in self.JS_CLASS_RE.finditer(code):
            entities.append(
                {"type": "CLASS", "name": m.group(1), "line": code.count("\n", 0, m.start()) + 1}
            )

        # Java classes
        for m in self.JAVA_CLASS_RE.finditer(code):
            entities.append(
                {"type": "CLASS", "name": m.group(1), "line": code.count("\n", 0, m.start()) + 1}
            )

        return entities

    def _extract_functions_and_methods(self, code: str, class_regions: List[Dict[str, int]]) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []

        # Python functions
        for m in self.PYTHON_FUNCTION_RE.finditer(code):
            start = m.start()
            line = code.count("\n", 0, start) + 1
            name = m.group(2)
            params = m.group(3) or ""
            ret_hint = (m.group(4) or "").strip()
            class_name = self._class_for_offset(start, class_regions)
            if class_name:
                entities.append({"type": "METHOD", "name": name, "class": class_name, "line": line})
            else:
                entities.append({"type": "FUNCTION", "name": name, "line": line})
            entities.extend(self._extract_parameters(params, name, line))
            if ret_hint:
                entities.append({"type": "RETURN", "name": name, "annotation": ret_hint, "line": line})

        # JavaScript functions
        for m in self.JS_FUNCTION_RE.finditer(code):
            start = m.start()
            line = code.count("\n", 0, start) + 1
            if m.group(1):
                name = m.group(1)
                params = m.group(2) or ""
            elif m.group(3):
                name = m.group(3)
                params = m.group(4) or ""
            elif m.group(5):
                name = m.group(5)
                params = m.group(6) or ""
            else:
                continue

            class_name = self._class_for_offset(start, class_regions)
            if class_name:
                entities.append({"type": "METHOD", "name": name, "class": class_name, "line": line})
            else:
                entities.append({"type": "FUNCTION", "name": name, "line": line})
            entities.extend(self._extract_parameters(params, name, line))

        # Java methods
        for m in self.JAVA_METHOD_RE.finditer(code):
            start = m.start()
            line = code.count("\n", 0, start) + 1
            name = m.group(1)
            params = m.group(2) or ""
            class_name = self._class_for_offset(start, class_regions)
            if class_name:
                entities.append({"type": "METHOD", "name": name, "class": class_name, "line": line})
            else:
                entities.append({"type": "FUNCTION", "name": name, "line": line})
            entities.extend(self._extract_parameters(params, name, line))

        # C/C++ functions
        for m in self.C_FUNCTION_RE.finditer(code):
            start = m.start()
            line = code.count("\n", 0, start) + 1
            name = m.group(1)
            params = m.group(2) or ""
            entities.append({"type": "FUNCTION", "name": name, "line": line})
            entities.extend(self._extract_parameters(params, name, line))

        return entities

    def _extract_parameters(self, params: str, function_name: str, line: int) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []
        for raw in self._split_params(params):
            part = raw.strip()
            if not part or part in {"/", "*"}:
                continue
            part = part.split("=")[0].strip()
            part = part.split(":")[0].strip()
            if not part:
                continue
            entities.append({"type": "PARAMETER", "name": part, "function": function_name, "line": line})
        return entities

    def _extract_variables(self, code: str) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []

        # Python variables (simple assignment)
        python_var_re = re.compile(r"^\s*([A-Za-z_]\w*)\s*[:=]", re.MULTILINE)
        for m in python_var_re.finditer(code):
            line_text = self._line_for_offset(code, m.start())
            if line_text.lstrip().startswith(("def ", "class ", "from ", "import ", "return ", "for ", "while ")):
                continue
            entities.append(
                {"type": "VARIABLE", "name": m.group(1), "line": code.count("\n", 0, m.start()) + 1}
            )

        # JavaScript variables (const, let, var)
        for m in self.JS_VAR_RE.finditer(code):
            line_text = self._line_for_offset(code, m.start())
            if line_text.lstrip().startswith(("function ", "class ", "import ", "export ")):
                continue
            entities.append(
                {"type": "VARIABLE", "name": m.group(1), "line": code.count("\n", 0, m.start()) + 1}
            )

        return entities

    def _class_regions(self, code: str) -> List[Dict[str, int]]:
        lines = code.splitlines(keepends=True)
        offsets: List[int] = []
        total = 0
        for ln in lines:
            offsets.append(total)
            total += len(ln)
        regions: List[Dict[str, int]] = []
        for idx, ln in enumerate(lines):
            match = self.PYTHON_CLASS_RE.match(ln)
            if match:
                regions.append({"name": match.group(1), "start": offsets[idx], "end": total})
                continue

            match = self.JS_CLASS_RE.match(ln)
            if match:
                regions.append({"name": match.group(1), "start": offsets[idx], "end": total})
                continue

            match = self.JAVA_CLASS_RE.match(ln)
            if match:
                regions.append({"name": match.group(1), "start": offsets[idx], "end": total})
                continue
        return regions

    def _class_for_offset(self, offset: int, class_regions: List[Dict[str, Any]]) -> str:
        for region in class_regions:
            if region["start"] <= offset < region["end"]:
                return str(region["name"])
        return ""

    def _line_for_offset(self, code: str, offset: int) -> str:
        start = code.rfind("\n", 0, offset)
        end = code.find("\n", offset)
        if start == -1:
            start = 0
        else:
            start += 1
        if end == -1:
            end = len(code)
        return code[start:end]

    def _split_params(self, text: str) -> List[str]:
        parts: List[str] = []
        current = []
        depth = 0
        for ch in text:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth = max(0, depth - 1)
            if ch == "," and depth == 0:
                parts.append("".join(current))
                current = []
            else:
                current.append(ch)
        if current:
            parts.append("".join(current))
        return parts
