import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List


class CASTTool:
    C_LIKE_EXTENSIONS = [".c", ".h", ".hpp", ".hh", ".hxx", ".cpp", ".cc", ".cxx"]
    C_TYPEDEF_RE = re.compile(r"^\s*typedef\b[^;]*\b([A-Za-z_]\w*)\s*;", re.MULTILINE)
    C_STRUCT_RE = re.compile(r"^\s*struct\s+([A-Za-z_]\w*)\s*\{", re.MULTILINE)
    C_UNION_RE = re.compile(r"^\s*union\s+([A-Za-z_]\w*)\s*\{", re.MULTILINE)
    C_ENUM_RE = re.compile(r"^\s*enum(?:\s+class|\s+struct)?\s+([A-Za-z_]\w*)\s*\{", re.MULTILINE)

    def extract(self, code: str) -> List[Dict[str, Any]]:
        if not code.strip():
            return []

        entities = self._extract_with_clang(code)
        if entities:
            strong_entities = [e for e in entities if e.get("type") != "IMPORT"]
            if strong_entities:
                return self._deduplicate_entities(entities)

        entities = self._extract_with_tree_sitter(code)
        if entities:
            return self._deduplicate_entities(entities)

        return self._deduplicate_entities(self._fallback_extract(code))

    def _extract_with_clang(self, code: str) -> List[Dict[str, Any]]:
        clang_bin = shutil.which("clang")
        if not clang_bin:
            return []

        # Try C and C++ modes to cover mixed repositories.
        attempts = [("c", ".c"), ("c++", ".cpp")]
        for language_name, suffix in attempts:
            dump = self._clang_ast_dump_json(clang_bin, code, language_name, suffix)
            if not dump:
                continue
            ast_json, source_file = dump
            entities = self._entities_from_clang_ast(
                ast_json,
                source_file=source_file,
                source_line_count=len(code.splitlines()),
                source_lines=code.splitlines(),
            )
            entities.extend(self._extract_includes(code))
            entities.extend(self._extract_cpp_keyword_entities(code))
            if entities:
                return entities
        return []

    def _clang_ast_dump_json(
        self, clang_bin: str, code: str, language_name: str, suffix: str
    ) -> tuple[Dict[str, Any], str] | None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / f"unit{suffix}"
            file_path.write_text(code, encoding="utf-8", errors="ignore")
            cmd = [
                clang_bin,
                "-Xclang",
                "-ast-dump=json",
                "-fsyntax-only",
                "-x",
                language_name,
                str(file_path),
            ]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            except Exception:
                return None
            # clang can return non-zero for missing includes/macros, but still provide
            # a useful partial AST dump on stdout.
            if not proc.stdout.strip():
                return None
            try:
                return json.loads(proc.stdout), str(file_path)
            except Exception:
                return None

    def _entities_from_clang_ast(
        self, root: Dict[str, Any], source_file: str, source_line_count: int, source_lines: List[str]
    ) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []
        source_name = Path(source_file).name

        def walk(
            node: Dict[str, Any],
            current_class: str = "",
            current_function: str = "",
            current_template: str = "",
        ) -> None:
            kind = str(node.get("kind", ""))
            loc = node.get("loc", {}) or {}
            line = self._node_line(node)
            name = str(node.get("name", "")).strip()
            in_source = self._node_in_source(
                node,
                source_name=source_name,
                source_line_count=source_line_count,
                source_lines=source_lines,
                entity_name=name,
            )

            next_class = current_class
            next_function = current_function
            next_template = current_template

            if in_source and kind in {"NamespaceDecl", "NamespaceAliasDecl"} and name:
                entities.append({"type": "NAMESPACE", "name": name, "line": line})

            elif in_source and kind in {"EnumDecl"} and name:
                enum_entity: Dict[str, Any] = {"type": "ENUM", "name": name, "line": line}
                if bool(node.get("scopedEnumTag", "")):
                    enum_entity["enum_kind"] = "enum_class"
                entities.append(enum_entity)

            elif in_source and kind in {"TypedefDecl", "TypeAliasDecl"} and name:
                entities.append({"type": "TYPEDEF", "name": name, "line": line})

            elif in_source and kind in {"ClassTemplateDecl", "FunctionTemplateDecl", "VarTemplateDecl", "TypeAliasTemplateDecl"} and name:
                entities.append({"type": "TEMPLATE", "name": name, "line": line})
                next_template = name
                if kind == "ClassTemplateDecl":
                    entities.append({"type": "CLASS", "name": name, "line": line})
                    next_class = name

            elif (
                in_source
                and kind in {"RecordDecl", "CXXRecordDecl", "ClassTemplateSpecializationDecl"}
                and name
            ):
                record_type = self._record_entity_type(node)
                entities.append({"type": record_type, "name": name, "line": line})
                if record_type in {"CLASS", "STRUCT", "UNION"}:
                    next_class = name

            elif in_source and kind in {"FunctionDecl", "FunctionTemplateDecl"} and name:
                entities.append({"type": "FUNCTION", "name": name, "line": line})
                next_function = name

                if self._has_non_void_return(node):
                    entities.append({"type": "RETURN", "name": name, "line": line})

            elif in_source and kind in {"CXXMethodDecl", "CXXConstructorDecl", "CXXDestructorDecl", "CXXConversionDecl"} and name:
                method_entity: Dict[str, Any] = {"type": "METHOD", "name": name, "line": line}
                if current_class:
                    method_entity["class"] = current_class
                method_entity["method_kind"] = self._method_kind(kind, name)
                if kind == "CXXConstructorDecl":
                    method_entity["is_constructor"] = True
                elif kind == "CXXDestructorDecl":
                    method_entity["is_destructor"] = True
                if str(name).startswith("operator"):
                    method_entity["is_operator_overload"] = True
                entities.append(method_entity)
                next_function = name
                if self._has_non_void_return(node):
                    entities.append({"type": "RETURN", "name": name, "line": line})

            elif in_source and kind == "ParmVarDecl" and name:
                param_entity: Dict[str, Any] = {"type": "PARAMETER", "name": name, "line": line}
                if current_function:
                    param_entity["function"] = current_function
                entities.append(param_entity)

            elif in_source and kind in {"TemplateTypeParmDecl", "NonTypeTemplateParmDecl", "TemplateTemplateParmDecl"} and name:
                tpl_param: Dict[str, Any] = {"type": "PARAMETER", "name": name, "line": line, "parameter_kind": "template"}
                if current_template:
                    tpl_param["template"] = current_template
                entities.append(tpl_param)

            elif in_source and kind in {"UsingDecl", "UsingDirectiveDecl"} and name:
                entities.append({"type": "IMPORT", "name": name, "line": line, "import_kind": "using"})

            elif in_source and kind == "TypeAliasTemplateDecl" and name:
                entities.append({"type": "TYPEDEF", "name": name, "line": line, "typedef_kind": "alias_template"})

            elif in_source and kind == "FriendDecl":
                friend_name = self._friend_name(node)
                if friend_name:
                    entities.append({"type": "METHOD", "name": friend_name, "line": line, "method_kind": "friend"})

            elif in_source and kind in {"VarDecl", "FieldDecl"} and name:
                var_entity: Dict[str, Any] = {"type": "VARIABLE", "name": name, "line": line}
                if current_function:
                    var_entity["function"] = current_function
                    var_entity["context"] = "local"
                elif current_class:
                    var_entity["class"] = current_class
                    var_entity["context"] = "class_attribute"
                else:
                    var_entity["context"] = "module"
                entities.append(var_entity)

            for child in self._children(node):
                walk(
                    child,
                    current_class=next_class,
                    current_function=next_function,
                    current_template=next_template,
                )

        walk(root)
        return entities

    def _friend_name(self, node: Dict[str, Any]) -> str:
        name = str(node.get("name", "")).strip()
        if name:
            return name
        for child in self._children(node):
            child_name = str(child.get("name", "")).strip()
            if child_name:
                return child_name
        return ""

    def _node_line(self, node: Dict[str, Any]) -> int | None:
        loc = node.get("loc", {}) or {}
        if isinstance(loc, dict) and isinstance(loc.get("line"), int):
            return int(loc["line"])
        range_obj = node.get("range", {}) or {}
        if isinstance(range_obj, dict):
            begin = range_obj.get("begin", {}) or {}
            if isinstance(begin, dict) and isinstance(begin.get("line"), int):
                return int(begin["line"])
        return None

    def _node_in_source(
        self,
        node: Dict[str, Any],
        source_name: str,
        source_line_count: int,
        source_lines: List[str],
        entity_name: str,
    ) -> bool:
        loc = node.get("loc", {}) or {}
        if isinstance(loc, dict):
            loc_file = loc.get("file")
            if isinstance(loc_file, str) and Path(loc_file).name == source_name:
                return True

        range_obj = node.get("range", {}) or {}
        if isinstance(range_obj, dict):
            begin = range_obj.get("begin", {}) or {}
            if isinstance(begin, dict):
                begin_file = begin.get("file")
                if isinstance(begin_file, str) and Path(begin_file).name == source_name:
                    return True

        # Fallback for macOS clang dumps where file can be omitted:
        # accept only nodes that map to a valid source line and whose name
        # appears in that line to reduce header noise.
        line = self._node_line(node)
        if isinstance(line, int) and 1 <= line <= max(1, source_line_count):
            if not entity_name:
                return False
            token = entity_name.split("::")[-1].strip("~")
            if not token:
                return False
            if token.startswith("__"):
                return False
            # Search in a small window because clang may point to macro lines.
            start = max(0, line - 2)
            end = min(len(source_lines), line + 3)
            for idx in range(start, end):
                line_text = source_lines[idx]
                if re.search(rf"\b{re.escape(token)}\b", line_text):
                    return True
        return False

    def _record_entity_type(self, node: Dict[str, Any]) -> str:
        tag_used = str(node.get("tagUsed", "")).lower()
        if tag_used == "struct":
            return "STRUCT"
        if tag_used == "union":
            return "UNION"
        if tag_used == "class":
            return "CLASS"
        kind = str(node.get("kind", ""))
        if kind == "CXXRecordDecl":
            return "CLASS"
        return "STRUCT"

    def _method_kind(self, kind: str, name: str) -> str:
        if kind == "CXXConstructorDecl":
            return "constructor"
        if kind == "CXXDestructorDecl":
            return "destructor"
        if kind == "CXXConversionDecl":
            return "conversion"
        if str(name).startswith("operator"):
            return "operator"
        return "method"

    def _children(self, node: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        children = node.get("inner", [])
        if not isinstance(children, list):
            return []
        return [x for x in children if isinstance(x, dict)]

    def _has_non_void_return(self, node: Dict[str, Any]) -> bool:
        qtype = ""
        type_obj = node.get("type", {})
        if isinstance(type_obj, dict):
            qtype = str(type_obj.get("qualType", ""))
        if not qtype:
            return False
        left = qtype.split("(", 1)[0].strip().lower()
        if not left:
            return False
        return left != "void"

    def _extract_with_tree_sitter(self, code: str) -> List[Dict[str, Any]]:
        # Optional fallback. If tree-sitter packages are missing, silently skip.
        try:
            from tree_sitter import Parser  # type: ignore[reportMissingImports]
            from tree_sitter_languages import get_language  # type: ignore[reportMissingImports]
        except Exception:
            return []

        parsers: List[tuple[str, Any]] = []
        try:
            parsers.append(("c", get_language("c")))
        except Exception:
            pass
        try:
            parsers.append(("cpp", get_language("cpp")))
        except Exception:
            pass
        if not parsers:
            return []

        best_entities: List[Dict[str, Any]] = []
        source = code.encode("utf-8", errors="ignore")
        for _, language in parsers:
            parser = Parser()
            parser.set_language(language)
            tree = parser.parse(source)
            entities = self._entities_from_tree_sitter(tree.root_node, code)
            entities.extend(self._extract_includes(code))
            entities.extend(self._extract_cpp_keyword_entities(code))
            if len(entities) > len(best_entities):
                best_entities = entities
        return best_entities

    def _entities_from_tree_sitter(self, root: Any, code: str) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []
        lines = code.splitlines()

        def text_of(node: Any) -> str:
            try:
                segment = code[node.start_byte:node.end_byte]
            except Exception:
                return ""
            return str(segment).strip()

        def node_name(node: Any, field_name: str) -> str:
            child = node.child_by_field_name(field_name)
            if child is None:
                return ""
            return text_of(child)

        def line_of(node: Any) -> int:
            return int(node.start_point[0]) + 1

        def walk(node: Any, current_class: str = "", current_function: str = "") -> None:
            node_type = str(getattr(node, "type", ""))
            next_class = current_class
            next_function = current_function

            if node_type in {"namespace_definition"}:
                name = node_name(node, "name")
                if name:
                    entities.append({"type": "NAMESPACE", "name": name, "line": line_of(node)})

            elif node_type in {"enum_specifier"}:
                name = node_name(node, "name")
                if name:
                    enum_entity: Dict[str, Any] = {"type": "ENUM", "name": name, "line": line_of(node)}
                    source_text = text_of(node)
                    if source_text.startswith("enum class") or source_text.startswith("enum struct"):
                        enum_entity["enum_kind"] = "enum_class"
                    entities.append(enum_entity)

            elif node_type in {"type_definition"}:
                name = self._extract_ts_typedef_name(node, code)
                if name:
                    entities.append({"type": "TYPEDEF", "name": name, "line": line_of(node)})

            elif node_type in {"template_declaration"}:
                name = self._extract_ts_template_name(node, code)
                if name:
                    entities.append({"type": "TEMPLATE", "name": name, "line": line_of(node)})
                for tname in self._extract_ts_template_param_names(node, code):
                    entities.append(
                        {
                            "type": "PARAMETER",
                            "name": tname,
                            "line": line_of(node),
                            "parameter_kind": "template",
                            "template": name or "",
                        }
                    )

            elif node_type in {"struct_specifier", "union_specifier", "class_specifier"}:
                name = node_name(node, "name")
                if name:
                    record_type = "CLASS"
                    if node_type == "struct_specifier":
                        record_type = "STRUCT"
                    elif node_type == "union_specifier":
                        record_type = "UNION"
                    entities.append({"type": record_type, "name": name, "line": line_of(node)})
                    next_class = name

            elif node_type in {"function_definition"}:
                declarator = node.child_by_field_name("declarator")
                name = self._extract_ts_declarator_name(declarator, code) if declarator else ""
                if name:
                    if current_class:
                        method_entity: Dict[str, Any] = {"type": "METHOD", "name": name, "line": line_of(node), "class": current_class}
                        if name == current_class:
                            method_entity["method_kind"] = "constructor"
                            method_entity["is_constructor"] = True
                        elif name == f"~{current_class}":
                            method_entity["method_kind"] = "destructor"
                            method_entity["is_destructor"] = True
                        elif name.startswith("operator"):
                            method_entity["method_kind"] = "operator"
                            method_entity["is_operator_overload"] = True
                        else:
                            method_entity["method_kind"] = "method"
                        entities.append(method_entity)
                    else:
                        entities.append({"type": "FUNCTION", "name": name, "line": line_of(node)})
                    next_function = name

            elif node_type in {"parameter_declaration"}:
                name = self._extract_ts_parameter_name(node, code)
                if name:
                    param: Dict[str, Any] = {"type": "PARAMETER", "name": name, "line": line_of(node)}
                    if current_function:
                        param["function"] = current_function
                    entities.append(param)

            elif node_type in {"field_declaration", "init_declarator", "declaration"}:
                for var_name in self._extract_ts_decl_names(node, code):
                    var: Dict[str, Any] = {"type": "VARIABLE", "name": var_name, "line": line_of(node)}
                    if current_function:
                        var["function"] = current_function
                        var["context"] = "local"
                    elif current_class:
                        var["class"] = current_class
                        var["context"] = "class_attribute"
                    else:
                        var["context"] = "module"
                    entities.append(var)

            for child in node.children:
                walk(child, current_class=next_class, current_function=next_function)

        walk(root)
        return entities

    def _extract_ts_declarator_name(self, declarator: Any, code: str) -> str:
        if declarator is None:
            return ""
        node_type = str(getattr(declarator, "type", ""))
        if node_type in {"identifier", "field_identifier"}:
            return code[declarator.start_byte:declarator.end_byte].strip()
        for child in getattr(declarator, "children", []):
            name = self._extract_ts_declarator_name(child, code)
            if name:
                return name
        return ""

    def _extract_ts_parameter_name(self, node: Any, code: str) -> str:
        declarator = node.child_by_field_name("declarator")
        if declarator is None:
            return ""
        return self._extract_ts_declarator_name(declarator, code)

    def _extract_ts_decl_names(self, node: Any, code: str) -> List[str]:
        out: List[str] = []
        for child in getattr(node, "children", []):
            name = self._extract_ts_declarator_name(child, code)
            if name and name not in out:
                out.append(name)
        return out

    def _extract_ts_typedef_name(self, node: Any, code: str) -> str:
        for child in getattr(node, "children", []):
            name = self._extract_ts_declarator_name(child, code)
            if name:
                return name
        return ""

    def _extract_ts_template_name(self, node: Any, code: str) -> str:
        for child in getattr(node, "children", []):
            ctype = str(getattr(child, "type", ""))
            if ctype in {"class_specifier", "struct_specifier", "union_specifier", "function_definition"}:
                name = self._extract_ts_declarator_name(child, code)
                if name:
                    return name
                name_field = child.child_by_field_name("name")
                if name_field is not None:
                    return code[name_field.start_byte:name_field.end_byte].strip()
        return ""

    def _extract_ts_template_param_names(self, node: Any, code: str) -> List[str]:
        names: List[str] = []
        for child in getattr(node, "children", []):
            ctype = str(getattr(child, "type", ""))
            if ctype in {"template_parameter_list", "type_parameter_declaration", "parameter_declaration"}:
                for grand in getattr(child, "children", []):
                    name = self._extract_ts_declarator_name(grand, code)
                    if name and name not in names:
                        names.append(name)
                # fallback: naive tokenization for `typename T`
                text = code[child.start_byte:child.end_byte]
                for m in re.finditer(r"\b(?:typename|class)\s+([A-Za-z_]\w*)", text):
                    n = m.group(1)
                    if n not in names:
                        names.append(n)
        return names

    def _fallback_extract(self, code: str) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []
        entities.extend(self._extract_includes(code))
        entities.extend(self._extract_cpp_keyword_entities(code))
        entities.extend(self._extract_c_regex_entities(code))
        return entities

    def _extract_c_regex_entities(self, code: str) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []

        for m in self.C_STRUCT_RE.finditer(code):
            entities.append({"type": "STRUCT", "name": m.group(1), "line": code.count("\n", 0, m.start()) + 1})
        for m in self.C_UNION_RE.finditer(code):
            entities.append({"type": "UNION", "name": m.group(1), "line": code.count("\n", 0, m.start()) + 1})
        for m in self.C_ENUM_RE.finditer(code):
            entities.append({"type": "ENUM", "name": m.group(1), "line": code.count("\n", 0, m.start()) + 1})
        for m in self.C_TYPEDEF_RE.finditer(code):
            entities.append({"type": "TYPEDEF", "name": m.group(1), "line": code.count("\n", 0, m.start()) + 1})

        lines = code.splitlines()
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line or "(" not in line or ")" not in line or "{" not in line:
                continue
            if line.startswith("#"):
                continue
            if line.startswith(("if ", "for ", "while ", "switch ", "return ", "typedef ", "struct ", "enum ", "union ")):
                continue
            if line.endswith(";"):
                continue

            signature = line.split("{", 1)[0].strip()
            m = re.search(r"([A-Za-z_]\w*)\s*\((.*)\)\s*$", signature)
            if not m:
                continue
            name = m.group(1)
            params = m.group(2) or ""
            if name in {"if", "for", "while", "switch"}:
                continue

            entities.append({"type": "FUNCTION", "name": name, "line": idx})

            head = signature[: signature.rfind(name)].strip()
            if not re.search(r"\bvoid\b", head, flags=re.IGNORECASE):
                entities.append({"type": "RETURN", "name": name, "line": idx})
            for p in self._split_c_params(params):
                if p in {"void", "..."}:
                    continue
                pname = self._extract_c_param_name(p)
                if pname:
                    entities.append({"type": "PARAMETER", "name": pname, "function": name, "line": idx})
        return entities

    def _split_c_params(self, params: str) -> List[str]:
        parts: List[str] = []
        current: List[str] = []
        depth = 0
        for ch in params:
            if ch in "([{<":
                depth += 1
            elif ch in ")]}>":
                depth = max(0, depth - 1)
            if ch == "," and depth == 0:
                part = "".join(current).strip()
                if part:
                    parts.append(part)
                current = []
            else:
                current.append(ch)
        tail = "".join(current).strip()
        if tail:
            parts.append(tail)
        return parts

    def _extract_c_param_name(self, param: str) -> str:
        cleaned = param.strip()
        cleaned = cleaned.split("=", 1)[0].strip()
        cleaned = cleaned.replace("*", " ").replace("&", " ")
        tokens = [t for t in re.split(r"\s+", cleaned) if t]
        if not tokens:
            return ""
        candidate = tokens[-1]
        candidate = candidate.strip()
        if not re.match(r"^[A-Za-z_]\w*$", candidate):
            return ""
        return candidate

    def _deduplicate_entities(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        seen = set()
        for e in entities:
            key = (
                e.get("type"),
                e.get("name"),
                e.get("line"),
                e.get("class"),
                e.get("function"),
                e.get("method_kind"),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(e)
        return out

    def _extract_includes(self, code: str) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []
        for idx, raw_line in enumerate(code.splitlines(), start=1):
            line = raw_line.strip()
            if not line.startswith("#include"):
                continue
            include_name = (
                line.replace("#include", "", 1).strip().strip("<>").strip('"')
            )
            if not include_name:
                continue
            entities.append({"type": "IMPORT", "name": include_name, "line": idx})
        return entities

    def _extract_cpp_keyword_entities(self, code: str) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []
        lines = code.splitlines()
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip().rstrip(";")
            if not line:
                continue

            m = re.match(r"^using\s+namespace\s+([A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)$", line)
            if m:
                entities.append({"type": "IMPORT", "name": m.group(1), "line": idx, "import_kind": "using_namespace"})
                continue

            m = re.match(r"^using\s+([A-Za-z_]\w*)\s*=\s*.+$", line)
            if m:
                entities.append({"type": "TYPEDEF", "name": m.group(1), "line": idx, "typedef_kind": "using_alias"})
                continue

            m = re.match(r"^friend\s+(?:class|struct)\s+([A-Za-z_]\w*)$", line)
            if m:
                entities.append({"type": "METHOD", "name": m.group(1), "line": idx, "method_kind": "friend"})
                continue

            m = re.match(r"^friend\s+.+\s+([A-Za-z_]\w*)\s*\(.*\)$", line)
            if m:
                entities.append({"type": "METHOD", "name": m.group(1), "line": idx, "method_kind": "friend"})
                continue

            m = re.match(r"^enum\s+class\s+([A-Za-z_]\w*)\b", line)
            if m:
                entities.append({"type": "ENUM", "name": m.group(1), "line": idx, "enum_kind": "enum_class"})
        return entities
