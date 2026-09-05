import ast
from typing import Any, Dict, List


class _ASTEntityVisitor(ast.NodeVisitor):
    def __init__(self, source: str, max_body_chars: int = 150_000) -> None:
        self._source = source
        self._max_body_chars = max(1, max_body_chars)
        self.entities: List[Dict[str, Any]] = []
        self._class_stack: List[str] = []
        self._class_is_dataclass_stack: List[bool] = []
        self._function_stack: List[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.entities.append(
                {
                    "type": "IMPORT",
                    "name": alias.name,
                    "line": getattr(node, "lineno", None),
                }
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        prefix = "." * int(getattr(node, "level", 0) or 0)
        for alias in node.names:
            full_name = f"{prefix}{module}.{alias.name}" if module else f"{prefix}{alias.name}"
            self.entities.append(
                {
                    "type": "IMPORT",
                    "name": full_name,
                    "line": getattr(node, "lineno", None),
                }
            )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        class_decorators = self._decorator_names(node.decorator_list)
        self.entities.append(
            {
                "type": "CLASS",
                "name": node.name,
                "line": getattr(node, "lineno", None),
            }
        )
        self._class_stack.append(node.name)
        self._class_is_dataclass_stack.append(self._is_dataclass_class(class_decorators))
        self.generic_visit(node)
        self._class_is_dataclass_stack.pop()
        self._class_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function_like(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function_like(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            self._emit_variables_from_target(target, getattr(node, "lineno", None))
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._emit_variables_from_target(node.target, getattr(node, "lineno", None))
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        self._emit_variables_from_target(node.target, getattr(node, "lineno", None))
        self.generic_visit(node)

    def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
        self._emit_variables_from_target(node.target, getattr(node, "lineno", None))
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._emit_variables_from_target(node.target, getattr(node, "lineno", None))
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._emit_variables_from_target(node.target, getattr(node, "lineno", None))
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        for item in node.items:
            if item.optional_vars is not None:
                self._emit_variables_from_target(item.optional_vars, getattr(item, "lineno", getattr(node, "lineno", None)))
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        for item in node.items:
            if item.optional_vars is not None:
                self._emit_variables_from_target(item.optional_vars, getattr(item, "lineno", getattr(node, "lineno", None)))
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if isinstance(node.name, str) and node.name:
            self._emit_variable(name=node.name, line=getattr(node, "lineno", None), context="except_alias")
        self.generic_visit(node)

    def visit_Global(self, node: ast.Global) -> None:
        for name in node.names:
            self._emit_variable(name=name, line=getattr(node, "lineno", None), scope="global")
        self.generic_visit(node)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        for name in node.names:
            self._emit_variable(name=name, line=getattr(node, "lineno", None), scope="nonlocal")
        self.generic_visit(node)

    def _visit_function_like(self, node: ast.AST) -> None:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return

        is_method = bool(self._class_stack) and not self._function_stack
        entity_type = "METHOD" if is_method else "FUNCTION"
        decorators = self._decorator_names(node.decorator_list)
        start_line = getattr(node, "lineno", None)
        end_line = getattr(node, "end_lineno", None)
        body_text, body_truncated = self._function_body_text(node)
        entity: Dict[str, Any] = {
            "type": entity_type,
            "name": node.name,
            "line": start_line,
            "start_line": start_line,
            "end_line": end_line,
            "args": self._arg_names_list(node),
            "body": body_text,
            "body_truncated": body_truncated,
        }
        if decorators:
            entity["decorators"] = decorators
            entity["is_staticmethod"] = "staticmethod" in decorators
            entity["is_classmethod"] = "classmethod" in decorators
            is_property_setter = any(d.endswith(".setter") for d in decorators)
            is_property_deleter = any(d.endswith(".deleter") for d in decorators)
            is_property_getter = "property" in decorators or any(d.endswith(".getter") for d in decorators)
            entity["is_property"] = is_property_getter or is_property_setter or is_property_deleter
            entity["is_property_setter"] = is_property_setter
            entity["is_property_deleter"] = is_property_deleter
            prop_name = self._property_name_from_decorators(decorators)
            if prop_name:
                entity["property_name"] = prop_name
        if is_method:
            entity["class"] = self._class_stack[-1]
        self.entities.append(entity)

        self.entities.extend(self._extract_params(node))
        if self._has_return(node):
            self.entities.append(
                {
                    "type": "RETURN",
                    "name": node.name,
                    "line": getattr(node, "lineno", None),
                }
            )

        self._function_stack.append(node.name)
        self.generic_visit(node)
        self._function_stack.pop()

    def _arg_names_list(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> List[str]:
        names: List[str] = []
        for a in node.args.posonlyargs:
            names.append(a.arg)
        for a in node.args.args:
            names.append(a.arg)
        if node.args.vararg:
            names.append(f"*{node.args.vararg.arg}")
        for a in node.args.kwonlyargs:
            names.append(a.arg)
        if node.args.kwarg:
            names.append(f"**{node.args.kwarg.arg}")
        return names

    def _function_body_text(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> tuple[str, bool]:
        seg = ast.get_source_segment(self._source, node, padded=False)
        if seg is not None:
            text = seg
        else:
            lines = self._source.splitlines()
            lo = (getattr(node, "lineno", 1) or 1) - 1
            hi = getattr(node, "end_lineno", None)
            if isinstance(hi, int) and hi > 0:
                hi = min(len(lines), hi)
            else:
                hi = min(len(lines), lo + 1)
            text = "\n".join(lines[lo:hi])
        truncated = len(text) > self._max_body_chars
        if truncated:
            text = text[: self._max_body_chars] + "\n... [truncated]"
        return text, truncated

    def _extract_params(self, node: ast.AST) -> List[Dict[str, Any]]:
        params: List[Dict[str, Any]] = []
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return params

        for arg in list(node.args.posonlyargs) + list(node.args.args) + list(node.args.kwonlyargs):
            params.append(
                {
                    "type": "PARAMETER",
                    "name": arg.arg,
                    "function": node.name,
                    "line": getattr(arg, "lineno", getattr(node, "lineno", None)),
                }
            )

        if node.args.vararg:
            params.append(
                {
                    "type": "PARAMETER",
                    "name": f"*{node.args.vararg.arg}",
                    "function": node.name,
                    "line": getattr(node.args.vararg, "lineno", getattr(node, "lineno", None)),
                }
            )

        if node.args.kwarg:
            params.append(
                {
                    "type": "PARAMETER",
                    "name": f"**{node.args.kwarg.arg}",
                    "function": node.name,
                    "line": getattr(node.args.kwarg, "lineno", getattr(node, "lineno", None)),
                }
            )
        return params

    def _has_return(self, node: ast.AST) -> bool:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return False
        if node.returns is not None:
            return True
        detector = _ReturnDetector()
        for stmt in node.body:
            detector.visit(stmt)
            if detector.has_return:
                return True
        return False

    def _emit_variables_from_target(self, target: ast.AST, line: int | None) -> None:
        if isinstance(target, ast.Name):
            self._emit_variable(name=target.id, line=getattr(target, "lineno", line))
            return

        if isinstance(target, ast.Attribute):
            if isinstance(target.value, ast.Name) and target.value.id == "self":
                self._emit_variable(
                    name=f"self.{target.attr}",
                    line=getattr(target, "lineno", line),
                    context="instance_attribute",
                )
            return

        if isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                self._emit_variables_from_target(element, line)
            return

        if isinstance(target, ast.Starred):
            self._emit_variables_from_target(target.value, line)

    def _decorator_names(self, decorators: List[ast.expr]) -> List[str]:
        names: List[str] = []
        for dec in decorators:
            name = self._decorator_name(dec)
            if name:
                names.append(name)
        return names

    def _decorator_name(self, decorator: ast.expr) -> str:
        if isinstance(decorator, ast.Name):
            return decorator.id
        if isinstance(decorator, ast.Attribute):
            base = self._decorator_name(decorator.value)
            return f"{base}.{decorator.attr}" if base else decorator.attr
        if isinstance(decorator, ast.Call):
            return self._decorator_name(decorator.func)
        return ""

    def _property_name_from_decorators(self, decorators: List[str]) -> str:
        for dec in decorators:
            if dec.endswith(".setter") or dec.endswith(".deleter") or dec.endswith(".getter"):
                return dec.rsplit(".", 1)[0]
        return ""

    def _is_dataclass_class(self, decorators: List[str]) -> bool:
        for dec in decorators:
            if dec == "dataclass" or dec.endswith(".dataclass"):
                return True
        return False

    def _emit_variable(
        self,
        name: str,
        line: int | None,
        scope: str | None = None,
        context: str | None = None,
    ) -> None:
        entity: Dict[str, Any] = {
            "type": "VARIABLE",
            "name": name,
            "line": line,
        }
        if self._class_stack:
            entity["class"] = self._class_stack[-1]
        if self._function_stack:
            entity["function"] = self._function_stack[-1]

        if context:
            entity["context"] = context
        else:
            if name.startswith("self."):
                entity["context"] = "instance_attribute"
            elif self._function_stack:
                entity["context"] = "local"
            elif self._class_stack:
                if self._class_is_dataclass_stack and self._class_is_dataclass_stack[-1] and "." not in name:
                    entity["context"] = "dataclass_field"
                else:
                    entity["context"] = "class_attribute"
            else:
                entity["context"] = "module"

        if scope:
            entity["scope"] = scope
        self.entities.append(entity)


class _ReturnDetector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.has_return = False

    def visit_Return(self, node: ast.Return) -> None:
        self.has_return = True

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        return

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return


class ASTTool:
    def extract(self, code: str, *, max_function_body_chars: int = 150_000) -> List[Dict[str, Any]]:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return []

        visitor = _ASTEntityVisitor(code, max_body_chars=max_function_body_chars)
        visitor.visit(tree)
        return visitor.entities
