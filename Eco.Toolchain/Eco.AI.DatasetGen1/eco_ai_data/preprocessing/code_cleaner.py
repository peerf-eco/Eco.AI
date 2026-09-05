import re


class CodeCleaner:
    def clean(self, code: str) -> str:
        code = code.replace("\r\n", "\n").replace("\r", "\n")
        code = code.replace("\t", "    ")
        code = self._strip_nulls(code)
        return self._collapse_excess_blank_lines(code)

    def _strip_nulls(self, code: str) -> str:
        return code.replace("\x00", "")

    def _collapse_excess_blank_lines(self, code: str) -> str:
        return re.sub(r"\n{4,}", "\n\n\n", code)
