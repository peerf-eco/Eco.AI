from __future__ import annotations

import ast
import hashlib
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from eco_ai_data.archive_algorithms.hybrid_regex_tool import HybridRegexTool
from eco_ai_data.archive_algorithms.openai_tool import HybridRegexOpenAITool
from eco_ai_data.labeling.entity_schema import is_valid_entity
from eco_ai_data.tools.ast_tool import ASTTool
from eco_ai_data.tools.c_ast_tool import CASTTool

_dotenv_loaded = False

# Окно размера функции (физические строки узла в исходнике)
_MIN_FUNCTION_LINES = 4
_MAX_FUNCTION_LINES = 60

# Ответы с такими подстроками (без учёта регистра) отбрасываются
_BAD_ANSWER_SUBSTRINGS = (
    "docstring",
    "this dataset",
    "dataset row",
    "training dataset",
    "the given context",
    "the context above",
    "provided context",
)
_BAD_ANSWER_WORD_CONTEXT = re.compile(r"\bcontext\b", re.IGNORECASE)
# Расплывчатые формулировки — отсекаем, чтобы не учить «красиво, но не точно»
_BAD_ANSWER_HEDGE_RE = re.compile(
    r"\b(likely|probably|presumably|possibly|seemingly)\b|"
    r"\bit\s+seems\b|"
    r"\bappears\s+to\b|"
    r"\bgenerally\s+speaking\b",
    re.IGNORECASE,
)


def _dotenv_candidate_paths() -> List[Path]:
    here = Path(__file__).resolve().parent
    return [
        Path.cwd() / ".env",
        here.parent.parent / ".env",
        here.parent.parent.parent / ".env",
    ]


def _parse_openai_key_from_env_file(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if not s.startswith("OPENAI_API_KEY"):
            continue
        _, _, rhs = s.partition("=")
        raw = rhs.strip()
        if "#" in raw and not (raw.startswith('"') or raw.startswith("'")):
            raw = raw.split("#", 1)[0].strip()
        return _strip_api_key_quotes(raw) or None
    return None


def _strip_api_key_quotes(raw: str) -> str:
    s = raw.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        s = s[1:-1]
    return s.strip()


def _load_dotenv_once() -> None:
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    _dotenv_loaded = True
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for p in _dotenv_candidate_paths():
        if p.is_file():
            load_dotenv(p, override=False)


@dataclass
class _BodySignals:
    has_if: bool = False
    has_if_with_else: bool = False
    has_loop: bool = False
    has_try: bool = False
    has_return: bool = False
    return_bool_flags: List[bool] = field(default_factory=list)
    if_count: int = 0
    nested_if: bool = False
    try_with_if_body: bool = False
    if_with_try_body: bool = False
    loop_with_if: bool = False
    mutation_in_loop: bool = False
    has_local_assign: bool = False
    loop_has_else: bool = False
    has_break_continue: bool = False

    @property
    def returns_only_boolish(self) -> bool:
        return bool(self.return_bool_flags) and all(self.return_bool_flags)

    @property
    def try_if_mix(self) -> bool:
        return self.try_with_if_body or self.if_with_try_body

    @property
    def hard_flow(self) -> bool:
        return self.if_count >= 3 or (self.nested_if and (self.has_try or self.loop_with_if))


def _body_statements_skip_docstring(node: ast.FunctionDef | ast.AsyncFunctionDef) -> List[ast.stmt]:
    stmts = list(node.body)
    if stmts and isinstance(stmts[0], ast.Expr):
        v = stmts[0].value
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            stmts = stmts[1:]
    return stmts


def _function_physical_lines(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    lo = getattr(node, "lineno", 1) or 1
    hi = getattr(node, "end_lineno", None)
    if isinstance(hi, int) and hi > 0:
        return hi - lo + 1
    return 1


def _is_stub_or_trivial(stmts: List[ast.stmt]) -> bool:
    if not stmts:
        return True
    if len(stmts) == 1:
        s0 = stmts[0]
        if isinstance(s0, ast.Pass):
            return True
        if isinstance(s0, ast.Expr) and isinstance(s0.value, ast.Constant) and s0.value.value is Ellipsis:
            return True
        if isinstance(s0, ast.Expr) and isinstance(s0.value, ast.Ellipsis):
            return True
        if isinstance(s0, ast.Raise):
            return False
    return False


def _scan_body_structure(stmts: List[ast.stmt]) -> _BodySignals:
    sig = _BodySignals()

    def walk_returns(n: ast.AST) -> None:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return
        if isinstance(n, ast.Return):
            sig.has_return = True
            if n.value is None:
                sig.return_bool_flags.append(False)
            elif isinstance(n.value, ast.Constant) and isinstance(n.value.value, bool):
                sig.return_bool_flags.append(True)
            elif isinstance(n.value, ast.Name) and n.value.id in ("True", "False"):
                sig.return_bool_flags.append(True)
            else:
                sig.return_bool_flags.append(False)
        for ch in ast.iter_child_nodes(n):
            walk_returns(ch)

    def walk_misc(n: ast.AST) -> None:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return
        if isinstance(n, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
            sig.has_loop = True
        for ch in ast.iter_child_nodes(n):
            walk_misc(ch)

    def stmt_list(block: List[ast.stmt], if_body_depth: int, loop_depth: int, try_depth: int) -> None:
        for st in block:
            dispatch(st, if_body_depth, loop_depth, try_depth)

    def dispatch(st: ast.stmt, if_body_depth: int, loop_depth: int, try_depth: int) -> None:
        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return
        if isinstance(st, ast.If):
            sig.has_if = True
            sig.if_count += 1
            if if_body_depth >= 1:
                sig.nested_if = True
            if st.orelse:
                sig.has_if_with_else = True
            if loop_depth > 0:
                sig.loop_with_if = True
            if try_depth > 0:
                sig.try_with_if_body = True
            stmt_list(st.body, if_body_depth + 1, loop_depth, try_depth)
            stmt_list(st.orelse, if_body_depth, loop_depth, try_depth)
            return
        if isinstance(st, (ast.For, ast.AsyncFor, ast.While)):
            sig.has_loop = True
            if st.orelse:
                sig.loop_has_else = True
            stmt_list(st.body, if_body_depth, loop_depth + 1, try_depth)
            stmt_list(st.orelse, if_body_depth, loop_depth, try_depth)
            return
        if isinstance(st, ast.Try):
            sig.has_try = True
            if if_body_depth > 0:
                sig.if_with_try_body = True
            stmt_list(st.body, if_body_depth, loop_depth, try_depth + 1)
            for h in st.handlers:
                stmt_list(h.body, if_body_depth, loop_depth, try_depth + 1)
            stmt_list(st.orelse, if_body_depth, loop_depth, try_depth)
            stmt_list(st.finalbody, if_body_depth, loop_depth, try_depth)
            return
        if isinstance(st, (ast.With, ast.AsyncWith)):
            stmt_list(st.body, if_body_depth, loop_depth, try_depth)
            return
        match_cls = getattr(ast, "Match", None)
        if match_cls is not None and isinstance(st, match_cls):
            for case in st.cases:
                stmt_list(case.body, if_body_depth, loop_depth, try_depth)
            return
        if isinstance(st, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            sig.has_local_assign = True
            if loop_depth > 0:
                sig.mutation_in_loop = True
        if isinstance(st, (ast.Break, ast.Continue)) and loop_depth > 0:
            sig.has_break_continue = True
        if isinstance(st, ast.Expr) and isinstance(
            st.value, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)
        ):
            sig.has_loop = True

    stmt_list(stmts, 0, 0, 0)
    for st in stmts:
        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        walk_returns(st)
        walk_misc(st)
    return sig


def _question_plan(qual: str, sig: _BodySignals) -> List[Tuple[str, str]]:
    """(question_type, question_text) — несколько типов на одну функцию."""
    out: List[Tuple[str, str]] = [
        ("FUNCTIONALITY", f"What does the function `{qual}` do?"),
    ]
    if sig.has_return:
        out.append(("RETURN_VALUE", f"What does the function `{qual}` return?"))
    if sig.has_if or sig.has_try:
        out.append(
            (
                "EDGE_CASES",
                f"What conditional branches, guards, or exceptional paths does `{qual}` implement?",
            )
        )
    elif sig.has_loop:
        out.append(
            (
                "EDGE_CASES",
                f"What happens when `{qual}` receives empty or minimal input while iterating?",
            )
        )
    if sig.has_loop:
        out.append(
            (
                "BEHAVIOR",
                f"How does `{qual}` iterate and update state while processing elements?",
            )
        )
    else:
        out.append(
            (
                "BEHAVIOR",
                f"How does `{qual}` process its arguments and produce its result?",
            )
        )
    if sig.has_return and sig.returns_only_boolish:
        out.append(
            (
                "YES_NO",
                f"Does `{qual}` communicate a yes/no or success state through boolean returns? When?",
            )
        )
    if sig.has_if:
        out.append(
            (
                "WHY_CHECK",
                f"In `{qual}`, what is the conditional expression after `if`, when is it truthy vs falsy in Python, "
                f"and which statements run in each case? Explain as guard → branches using that expression, not "
                f"generic engineering motivation.",
            )
        )
    alternate_return_paths = sig.has_if and sig.has_return and len(sig.return_bool_flags) >= 2
    if sig.has_if_with_else or sig.has_try or alternate_return_paths:
        out.append(
            (
                "WHY_FALLBACK",
                f"In `{qual}`, what distinct runtime outcomes are routed to different branches or returns, and which "
                f"tests or `try`/`except` edges select each outcome? Stay tied to the control flow in the snippet.",
            )
        )
    if sig.has_if:
        out.append(
            (
                "COUNTERFACTUAL",
                f"What could go wrong if the main `if` condition in `{qual}` were removed or always true?",
            )
        )
    elif sig.has_loop:
        out.append(
            (
                "COUNTERFACTUAL",
                f"What would change if the loop in `{qual}` never ran (empty collection or early break)?",
            )
        )
    out.append(
        (
            "BUG_SAFETY",
            f"Is `{qual}` safe to call as written? What invariants or preconditions does it assume?",
        )
    )
    if sig.has_if or sig.has_loop or sig.has_try:
        out.append(
            (
                "BUG_EDGE",
                f"What subtle bugs, edge cases, or stale state could still appear in `{qual}`?",
            )
        )
    if sig.nested_if:
        out.append(
            (
                "NESTED_LOGIC",
                f"In `{qual}`, how does the outer conditional relate to the inner one: which inner branch can run "
                f"only after which outcomes of the outer test?",
            )
        )
    if sig.try_if_mix:
        out.append(
            (
                "TRY_CONTROL_MIX",
                f"In `{qual}`, how do `try`/`except` paths and `if` paths interact: which exceptions or failures bypass "
                f"which returns shown in this function?",
            )
        )
    if sig.mutation_in_loop:
        out.append(
            (
                "LOOP_STATE",
                f"In `{qual}`, what names are written inside the loop body, and how can a value from one iteration "
                f"affect the next iteration's behavior?",
            )
        )
    if sig.loop_with_if and sig.has_break_continue:
        out.append(
            (
                "CONTROL_AMBIGUITY",
                f"In `{qual}`, how can `break` or `continue` change which guarded (`if`) paths run, and what state is "
                f"skipped or left partial when the loop exits early?",
            )
        )
    if sig.hard_flow:
        out.append(
            (
                "FLOW_COMPLEXITY",
                f"In `{qual}`, outline the main competing control paths (order of checks and early exits). What "
                f"inputs exercise the longest vs shortest path through the function as written?",
            )
        )
    seen: Set[str] = set()
    uniq: List[Tuple[str, str]] = []
    for qt, q in out:
        k = qt + "\0" + q
        if k in seen:
            continue
        seen.add(k)
        uniq.append((qt, q))
    return uniq[:22]


def _answer_passes_quality_filters(answer: str) -> bool:
    low = answer.lower()
    for s in _BAD_ANSWER_SUBSTRINGS:
        if s in low:
            return False
    if _BAD_ANSWER_WORD_CONTEXT.search(answer):
        return False
    if _BAD_ANSWER_HEDGE_RE.search(answer):
        return False
    return True


class LabelEngine:
    _max_qa_context_chars = 400_000
    _max_openai_prompt_context_chars = 120_000

    def __init__(
        self,
        tool_name: str = "ast",
        openai_model: str = "gpt-4o-mini",
        openai_api_key: str = "",
        *,
        dataset_mode: str = "generation",
        qa_answers_via_openai: bool = True,
        max_qa_pairs_per_file: Optional[int] = None,
        include_context: bool = False,
    ) -> None:
        self.tool_name = tool_name
        self._openai_model = openai_model
        self._openai_api_key = (openai_api_key or "").strip()
        self._dataset_mode = str(dataset_mode or "generation").strip().lower()
        if self._dataset_mode not in {"generation", "documentation"}:
            self._dataset_mode = "generation"
        self._qa_answers_via_openai = qa_answers_via_openai
        self._include_context = include_context
        self._max_qa_pairs_per_file = max_qa_pairs_per_file if (max_qa_pairs_per_file or 0) > 0 else None
        self._qa_openai_skip_logged = False
        self.tool = self._build_tool(tool_name, openai_model, openai_api_key)

    def label(self, code: str) -> List[Dict[str, Any]]:
        entities = self.tool.extract(code)
        normalized = [self._normalize_entity(e) for e in entities]
        return [e for e in normalized if is_valid_entity(e)]

    def generate_qa_pairs(self, code: str, file_path: str = "") -> List[Dict[str, Any]]:
        if self._dataset_mode == "documentation":
            return self._generate_documentation_pairs(code, file_path=file_path, limit=self._max_qa_pairs_per_file)
        # Поле называется qa_pairs по историческим причинам, но здесь это пары для code generation.
        ext = Path(file_path).suffix.lower()
        if ext in {".c", ".h", ".hpp", ".hh", ".hxx", ".cpp", ".cc", ".cxx"} or self.tool_name == "c_ast":
            return self._generate_generation_pairs_c_family(code, self._max_qa_pairs_per_file)
        return self._generate_generation_pairs_python(code, self._max_qa_pairs_per_file)

    def _generate_documentation_pairs(self, code: str, file_path: str, limit: Optional[int]) -> List[Dict[str, Any]]:
        ext = Path(file_path).suffix.lower()
        if ext in {".c", ".h", ".hpp", ".hh", ".hxx", ".cpp", ".cc", ".cxx"} or self.tool_name == "c_ast":
            return self._generate_documentation_pairs_c_family(code, limit)
        return self._generate_documentation_pairs_python(code, limit)

    def _generate_documentation_pairs_python(self, code: str, limit: Optional[int]) -> List[Dict[str, Any]]:
        pairs: List[Dict[str, Any]] = []
        seen_hashes: Set[str] = set()
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return pairs
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                setattr(child, "parent", parent)

        candidates: List[ast.FunctionDef | ast.AsyncFunctionDef] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                candidates.append(node)
        candidates.sort(key=lambda n: (getattr(n, "lineno", 0), getattr(n, "col_offset", 0)))

        for node in candidates:
            if not self._should_emit_qa_for_function(node):
                continue
            stmts = _body_statements_skip_docstring(node)
            if _is_stub_or_trivial(stmts):
                continue
            phys = _function_physical_lines(node)
            if phys < _MIN_FUNCTION_LINES or phys > _MAX_FUNCTION_LINES:
                continue

            qual = self._python_qualified_name(node)
            doc = ast.get_docstring(node)
            doc_hint = self._first_paragraph(doc) if doc else None
            sig = _scan_body_structure(stmts)
            fn_ctx = self._clip_context(self._function_source_segment(code, node))

            for qtype, question in _question_plan(qual, sig):
                h = hashlib.sha256(f"{qtype}\n{question}\n{fn_ctx[:2000]}".encode()).hexdigest()[:40]
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)

                answer = self._openai_doc_answer(question=question, function_source=fn_ctx, doc_hint=doc_hint, qtype=qtype)
                if self._qa_answers_via_openai and not answer:
                    self._log_openai_qa_skip_once()
                if not answer:
                    answer = self._fallback_doc_answer(node_name=node.name, doc_hint=doc_hint, qtype=qtype)
                if not _answer_passes_quality_filters(answer):
                    continue
                pairs.append(
                    {
                        "question": question,
                        "context": fn_ctx,
                        "answer": answer,
                        "question_type": qtype,
                    }
                )
                if limit is not None and len(pairs) >= limit:
                    return pairs
        return pairs

    def _generate_documentation_pairs_c_family(self, code: str, limit: Optional[int]) -> List[Dict[str, Any]]:
        pairs: List[Dict[str, Any]] = []
        for signature, fn_src in self._extract_c_like_functions(code):
            name = signature.split("(", 1)[0].split()[-1] if "(" in signature else "function"
            question = f"What does the function `{name}` do?"
            answer = self._openai_doc_answer(question=question, function_source=fn_src, doc_hint=None, qtype="FUNCTIONALITY")
            if self._qa_answers_via_openai and not answer:
                self._log_openai_qa_skip_once()
            if not answer:
                answer = f"The function `{name}` is implemented in the provided C/C++ source and should be inferred from its body."
            if not _answer_passes_quality_filters(answer):
                continue
            pairs.append(
                {
                    "question": question,
                    "context": fn_src,
                    "answer": answer,
                    "question_type": "FUNCTIONALITY",
                }
            )
            if limit is not None and len(pairs) >= limit:
                return pairs
        return pairs

    def _fallback_doc_answer(self, node_name: str, doc_hint: Optional[str], qtype: str) -> str:
        if doc_hint:
            if qtype == "FUNCTIONALITY":
                return doc_hint
            return f"{doc_hint} (Focus: {qtype.replace('_', ' ').lower()}.)"
        return (
            f"The symbol `{node_name}` has no inline documentation string; infer the answer only from the "
            f"Python source of the function shown."
        )

    def _openai_doc_answer(
        self, question: str, function_source: str, doc_hint: Optional[str], qtype: str
    ) -> Optional[str]:
        if not self._qa_answers_via_openai:
            return None
        key = self._effective_openai_key()
        if not key:
            return None
        try:
            from openai import OpenAI
        except Exception:
            return None
        cap = self._max_openai_prompt_context_chars
        src = (
            function_source
            if len(function_source) <= cap
            else function_source[:cap] + "\n\n[source truncated for model input]"
        )
        doc_block = (
            f"Authoritative excerpt from the function's leading documentation string:\n{doc_hint}\n\n"
            if doc_hint
            else ""
        )
        user = (
            f"{doc_block}"
            f"Question type: {qtype}\n"
            f"Question:\n{question}\n\n"
            f"Function source:\n{src}\n\n"
            "Write a concise, factual answer in plain prose (no markdown headings). "
            "Base the answer only on the source. "
            "Do not use the words: docstring, context, dataset."
        )
        system = (
            "You produce answers for a code question-answer dataset. "
            "Be precise and short; prefer explicit control-flow facts from source."
        )
        try:
            client = OpenAI(api_key=key)
            r = client.chat.completions.create(
                model=self._openai_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.15,
                max_tokens=900,
            )
            choice = r.choices[0].message
            text = getattr(choice, "content", None) or ""
            text = str(text).strip()
            if text and _answer_passes_quality_filters(text):
                return text
            return None
        except Exception:
            return None

    def _generate_generation_pairs_python(self, code: str, limit: Optional[int]) -> List[Dict[str, Any]]:
        pairs: List[Dict[str, Any]] = []
        seen_hashes: Set[str] = set()
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return pairs
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                setattr(child, "parent", parent)

        candidates: List[ast.FunctionDef | ast.AsyncFunctionDef] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                candidates.append(node)
        candidates.sort(key=lambda n: (getattr(n, "lineno", 0), getattr(n, "col_offset", 0)))

        for node in candidates:
            if not self._should_emit_qa_for_function(node):
                continue
            stmts = _body_statements_skip_docstring(node)
            if _is_stub_or_trivial(stmts):
                continue
            phys = _function_physical_lines(node)
            if phys < _MIN_FUNCTION_LINES or phys > _MAX_FUNCTION_LINES:
                continue

            fn_src = self._clip_context(self._function_source_segment(code, node))
            signature = self._python_signature_from_source(fn_src)
            if not signature:
                continue
            qual = self._python_qualified_name(node)
            question = self._build_generation_question(signature)
            h = hashlib.sha256(f"{qual}\n{signature}\n{fn_src[:2000]}".encode()).hexdigest()[:40]
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            context = self._maybe_build_context(signature=signature, function_source=fn_src)
            pairs.append(
                {
                    "question": question,
                    "context": context,
                    "answer": fn_src,
                    "question_type": "IMPLEMENTATION",
                }
            )
            if limit is not None and len(pairs) >= limit:
                return pairs
        return pairs

    def _should_emit_qa_for_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        par = getattr(node, "parent", None)
        if isinstance(par, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return False
        return True

    def _clip_context(self, text: str) -> str:
        cap = self._max_qa_context_chars
        if len(text) > cap:
            return text[: cap - 32] + "\n\n... [truncated]"
        return text

    def _build_generation_question(self, signature: str) -> str:
        return (
            "Implement function with below signature using ACOM component-based architecture. "
            "The signature is:\n\n"
            f"{signature}"
        )

    def _python_signature_from_source(self, function_source: str) -> str:
        lines = function_source.splitlines()
        buf: List[str] = []
        started = False
        for line in lines:
            stripped = line.strip()
            if not started and (stripped.startswith("def ") or stripped.startswith("async def ")):
                started = True
            if not started:
                continue
            buf.append(line)
            if ":" in line:
                break
        if not buf:
            return ""
        sig = "\n".join(buf)
        if ":" in sig:
            sig = sig.rsplit(":", 1)[0] + ":"
        return sig.strip()

    def _maybe_build_context(self, signature: str, function_source: str) -> str:
        if not self._include_context:
            return ""
        if self._qa_answers_via_openai:
            text = self._openai_generation_context(signature, function_source)
            if text:
                return text
            self._log_openai_qa_skip_once()
        return self._fallback_generation_context(signature)

    def _fallback_generation_context(self, signature: str) -> str:
        arg_part = ""
        if "(" in signature and ")" in signature:
            arg_part = signature.split("(", 1)[1].rsplit(")", 1)[0].strip()
        if not arg_part:
            return "Function receives required inputs defined by the signature and should produce deterministic output."
        return (
            "Function receives parameters declared in the signature ("
            + arg_part
            + "). Inputs should be validated and processed according to ACOM component responsibilities."
        )

    def _log_openai_qa_skip_once(self) -> None:
        if self._qa_openai_skip_logged:
            return
        self._qa_openai_skip_logged = True
        if not self._effective_openai_key():
            print(
                "[eco-ai-data] Context: OPENAI_API_KEY не найден (env и .env в cwd / Eco.AI.Data / родитель репо). "
                "Контекст будет собран по шаблону. Для AI-контекста уберите --no-qa-openai и передайте ключ.",
                file=sys.stderr,
            )
        else:
            print(
                "[eco-ai-data] Context: OpenAI вернул пустой ответ или запрос упал (сеть, квота, модель). "
                "Смотри лог/повтори запуск.",
                file=sys.stderr,
            )

    def _effective_openai_key(self) -> Optional[str]:
        _load_dotenv_once()
        if self._openai_api_key:
            k = _strip_api_key_quotes(self._openai_api_key)
            if k:
                return k
        env = _strip_api_key_quotes(os.environ.get("OPENAI_API_KEY", ""))
        if env:
            return env
        for p in _dotenv_candidate_paths():
            k = _parse_openai_key_from_env_file(p)
            if k:
                return k
        return None

    def _openai_generation_context(self, signature: str, function_source: str) -> Optional[str]:
        key = self._effective_openai_key()
        if not key:
            return None
        try:
            from openai import OpenAI
        except Exception:
            return None
        cap = self._max_openai_prompt_context_chars
        src = (
            function_source
            if len(function_source) <= cap
            else function_source[:cap] + "\n\n[source truncated for model input]"
        )
        user = (
            "Write one concise context sentence (max 35 words) for code-generation training.\n"
            "Mention expected inputs and high-level behavior only from the source.\n"
            "No markdown, no hedge words, no references to datasets.\n\n"
            f"Signature:\n{signature}\n\n"
            f"Function source:\n{src}\n"
        )
        system = (
            "You create compact task context for implementing existing functions."
        )
        try:
            client = OpenAI(api_key=key)
            r = client.chat.completions.create(
                model=self._openai_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.1,
                max_tokens=120,
            )
            choice = r.choices[0].message
            text = getattr(choice, "content", None) or ""
            text = str(text).strip()
            if text and _answer_passes_quality_filters(text):
                return text
            return None
        except Exception:
            return None

    def _generate_generation_pairs_c_family(self, code: str, limit: Optional[int]) -> List[Dict[str, Any]]:
        pairs: List[Dict[str, Any]] = []
        seen_hashes: Set[str] = set()
        for signature, fn_src in self._extract_c_like_functions(code):
            question = self._build_generation_question(signature)
            h = hashlib.sha256(f"{signature}\n{fn_src[:2000]}".encode()).hexdigest()[:40]
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            context = self._maybe_build_context(signature=signature, function_source=fn_src)
            pairs.append(
                {
                    "question": question,
                    "context": context,
                    "answer": fn_src,
                    "question_type": "IMPLEMENTATION",
                }
            )
            if limit is not None and len(pairs) >= limit:
                return pairs
        return pairs

    def _extract_c_like_functions(self, code: str) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        lines = code.splitlines()
        n = len(lines)
        i = 0
        in_block_comment = False
        while i < n:
            line = lines[i]
            stripped_line = line.strip()
            if in_block_comment:
                if "*/" in stripped_line:
                    in_block_comment = False
                i += 1
                continue
            if stripped_line.startswith("/*"):
                if "*/" not in stripped_line:
                    in_block_comment = True
                i += 1
                continue
            if stripped_line.startswith(("*", "//", "#")):
                i += 1
                continue
            if "(" not in line and i + 1 < n:
                i += 1
                continue
            sig_lines: List[str] = []
            paren_depth = 0
            saw_paren = False
            j = i
            header_done = False
            while j < n:
                cur = lines[j]
                stripped = cur.strip()
                if not sig_lines and not stripped:
                    j += 1
                    continue
                sig_lines.append(cur)
                # remove obvious inline comments to reduce false positives
                clean = re.sub(r"//.*$", "", cur)
                paren_depth += clean.count("(")
                paren_depth -= clean.count(")")
                saw_paren = saw_paren or "(" in clean
                if "{" in clean and saw_paren and paren_depth == 0:
                    header_done = True
                    break
                if ";" in clean and not header_done:
                    break
                if "}" in clean and not saw_paren:
                    break
                j += 1
            if not header_done:
                i += 1
                continue
            header = "\n".join(sig_lines)
            header_pre = header.split("{", 1)[0].strip()
            if not self._is_c_like_function_header(header_pre):
                i += 1
                continue
            body_lines: List[str] = []
            brace = 0
            k = i
            started = False
            while k < n:
                l = lines[k]
                body_lines.append(l)
                code_only = self._strip_c_line_comments(l)
                brace += code_only.count("{")
                brace -= code_only.count("}")
                if "{" in code_only:
                    started = True
                if started and brace <= 0:
                    break
                k += 1
            fn_src = "\n".join(body_lines).strip()
            if not fn_src or "{" not in fn_src or "}" not in fn_src:
                i += 1
                continue
            signature = self._normalize_c_signature(header_pre) + " { ... }"
            out.append((signature, fn_src))
            i = k + 1
        return out

    def _normalize_c_signature(self, header_pre: str) -> str:
        # Convert multi-line C/C++ signatures to one line for cleaner prompts.
        return " ".join(header_pre.split()).strip()

    def _is_c_like_function_header(self, header_pre: str) -> bool:
        scrub = re.sub(r"/\*.*?\*/", " ", header_pre, flags=re.DOTALL)
        scrub = re.sub(r"//.*", " ", scrub)
        one = " ".join(scrub.split())
        if not one or "(" not in one or ")" not in one:
            return False
        if one.count("(") > 3:
            return False
        low = one.lower()
        if low.startswith(("if ", "for ", "while ", "switch ", "catch ")):
            return False
        if "typedef " in low:
            return False
        if one.endswith(")") and ("=" in one or "return " in low):
            return False
        if one.endswith(";"):
            return False
        func_name_re = re.compile(
            r"(?:^|[\s*&])([~A-Za-z_]\w*(?:::[~A-Za-z_]\w*)*|operator\s*[^\s(]+)\s*\("
        )
        return bool(func_name_re.search(one))

    def _strip_c_line_comments(self, line: str) -> str:
        idx = line.find("//")
        if idx < 0:
            return line
        return line[:idx]

    def _build_tool(self, tool_name: str, openai_model: str, openai_api_key: str):
        if tool_name == "ast":
            return ASTTool()
        if tool_name == "c_ast":
            return CASTTool()
        if tool_name == "regex":
            return HybridRegexTool()
        if tool_name == "openai":
            return HybridRegexOpenAITool(model=openai_model, api_key=openai_api_key or None)
        raise ValueError(f"Unsupported tool: {tool_name}. Supported tools: ast, c_ast, regex, openai")

    def _function_source_segment(self, code: str, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        seg = ast.get_source_segment(code, node, padded=False)
        if seg is not None:
            return seg
        lines = code.splitlines()
        lo = (getattr(node, "lineno", 1) or 1) - 1
        hi = getattr(node, "end_lineno", None)
        if isinstance(hi, int) and hi > 0:
            hi = min(len(lines), hi)
        else:
            hi = min(len(lines), lo + 1)
        return "\n".join(lines[lo:hi])

    def _normalize_entity(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        out = dict(entity)
        out["type"] = str(out.get("type", "")).upper()
        out["name"] = str(out.get("name", "")).strip()
        if "line" in out:
            try:
                out["line"] = int(out["line"])
            except Exception:
                out.pop("line", None)
        return out

    def _python_qualified_name(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
        qual = node.name
        if hasattr(node, "parent") and isinstance(getattr(node, "parent", None), ast.ClassDef):
            qual = f"{node.parent.name}.{node.name}"  # type: ignore[attr-defined]
        return qual

    def _first_paragraph(self, doc: str) -> str:
        text = doc.strip()
        if not text:
            return ""
        parts = re.split(r"\n\s*\n", text, maxsplit=1)
        return parts[0].strip()

