import re

from ..results.Result import Result
from .Tool import Tool


class CDD(Tool):
    def __init__(self, command: str):
        super().__init__(command, "CDD")

    def can_handle(self, file: str) -> bool:
        return file.endswith(".ine")

    def parse_additional(self, result: Result):
        m = re.search(
            r"begin\s+(\d+)\s+[\s\S]*begin\s+(\d+)\s+[\s\S]*end", result.stdout
        )
        if m is None:
            result.answer = "invalid"
        else:
            result.additional_info["output_constraints"] = str(m.group(1))
            result.additional_info["output_constraints_min"] = str(m.group(2))
            result.answer = "success"
