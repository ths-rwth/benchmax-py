import re

from .. import options
from ..results.Result import Result
from .Tool import Tool


class cvc5(Tool):
    def __init__(self, command: str):
        super().__init__(command, "Z3")

    def get_command_line(self, file: str) -> str:
        res = self.binary + " " + self.arguments
        if options.args().statistics:
            res += " --stats --stats-internal"
        return res  + " " + file

    def can_handle(self, file: str) -> bool:
        return file.endswith(".smt2")

    def parse_additional(self, result: Result):
        if "unsat" in result.stdout:
            result.answer = "unsat"
        elif "sat" in result.stdout:
            result.answer = "sat"
        elif "unknown" in result.stdout:
            result.answer = "unknown"
        elif "out of memory" in result.stdout:
            result.answer = "memout"
        else:
            result.answer = "invalid"

        if options.args().statistics:
            for line in (line for line in result.stderr.splitlines() if '=' in line):
                key_value_pair = line.split('=', maxsplit=1)
                result.additional_info[key_value_pair[0].strip()] = key_value_pair[1].strip()