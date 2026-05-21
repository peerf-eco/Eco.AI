import json
import re
from typing import Any, Dict, List, Optional


class HybridRegexOpenAITool:
    FUNCTION_CANDIDATE_RE = re.compile(r"(?:async\s+def|def)\s+[A-Za-z_]\w*\s*\([^)]*\)\s*(?:->\s*[^:\n]+)?\s*:")
    CLASS_CANDIDATE_RE = re.compile(r"class\s+[A-Za-z_]\w*\s*(?:\([^)]*\))?\s*:")
    IMPORT_CANDIDATE_RE = re.compile(r"^\s*(?:from\s+.+\s+import\s+.+|import\s+.+)$", re.MULTILINE)

    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None) -> None:
        self.model = model
        self.api_key = api_key

    def extract(self, code: str) -> List[Dict[str, Any]]:
        candidates = self._extract_candidates(code)
        if not candidates:
            return []
        try:
            from openai import OpenAI
        except Exception:
            return self._fallback_entities(candidates)
        try:
            client = OpenAI(api_key=self.api_key) if self.api_key else OpenAI()
            content = self._prompt(candidates)
            response = client.responses.create(
                model=self.model,
                input=content,
                temperature=0,
            )
            text = self._response_text(response)
            data = json.loads(text)
            if isinstance(data, list):
                return [x for x in data if isinstance(x, dict)]
            return []
        except Exception:
            return self._fallback_entities(candidates)

    def _extract_candidates(self, code: str) -> str:
        matches: List[str] = []
        for pattern in [self.FUNCTION_CANDIDATE_RE, self.CLASS_CANDIDATE_RE, self.IMPORT_CANDIDATE_RE]:
            for m in pattern.finditer(code):
                snippet = self._line_for_offset(code, m.start())
                if snippet:
                    matches.append(snippet.strip())
        unique = []
        seen = set()
        for x in matches:
            if x not in seen:
                seen.add(x)
                unique.append(x)
        return "\n".join(unique)

    def _prompt(self, candidate_lines: str) -> str:
        return (
            "Extract structured entities as JSON list. "
            "Allowed types: FUNCTION, CLASS, IMPORT, METHOD, PARAMETER, RETURN, VARIABLE. "
            "Every item must have keys: type, name. "
            "Optional keys: class, function, line, annotation. "
            "Return only JSON.\n\n"
            f"Code candidates:\n{candidate_lines}"
        )

    def _response_text(self, response: Any) -> str:
        if hasattr(response, "output_text"):
            return str(response.output_text)
        if isinstance(response, dict):
            return json.dumps(response)
        return str(response)

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

    def _fallback_entities(self, candidates: str) -> List[Dict[str, Any]]:
        entities: List[Dict[str, Any]] = []
        for line in candidates.splitlines():
            l = line.strip()
            if l.startswith("def ") or l.startswith("async def "):
                name = l.split("def ", 1)[1].split("(", 1)[0].strip()
                entities.append({"type": "FUNCTION", "name": name})
            elif l.startswith("class "):
                name = l.split("class ", 1)[1].split("(", 1)[0].split(":", 1)[0].strip()
                entities.append({"type": "CLASS", "name": name})
            elif l.startswith("import ") or l.startswith("from "):
                entities.append({"type": "IMPORT", "name": l})
        return entities
