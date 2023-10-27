import logging
import re

import options
from results.Result import Result
from tools.Tool import Tool


def get_status_from_output(result: Result) -> str:
    if "GNU MP: Cannot allocate memory" in result.stderr:
        return "memout"
    if "Minisat::OutOfMemoryException" in result.stderr:
        return "memout"
    return "segfault"


def parse_stats(result: Result) -> bool:
    raw_output = result.stdout
    i = raw_output.find("(")
    if i < 0:
        return True

    r_category = re.compile(
        r"\(:(?P<prefix>\S+)\s+\(\s*(?P<values>(?::\S+\s+\S+\s*)+)(?P<tail>\)\s*\)\s*)"
    )

    r_values = re.compile(r":(?P<key>\S+)\s+(?P<val>[^\s):]+)")

    m = re.match(r_category, raw_output[i:])
    if m is None:
        return False

    while m != None:
        values = re.finditer(r_values, m.group("values"))
        for v in values:
            result.additional_info[m.group("prefix") + "_" + v.group("key")] = v.group(
                "val"
            )
        i += m.end()
        m = re.match(r_category, raw_output[i:])

    return True


class SMTRAT(Tool):
    def __init__(self, command: str):
        super().__init__(command, "SMTRAT")

    def get_command_line(self, file: str) -> str:
        res = self.binary + " " + self.arguments + " " + file
        if options.args().statistics:
            res += " --stats.print"
        return res

    def parse_additional(self, result: Result):
        match result.exit_code:
            case 2:
                result.answer = "sat"
            case 3:
                result.answer = "unsat"
            case 4:
                result.answer = "unknown"
            case 5:
                result.answer = "wrong"
            case 9:
                result.answer = "nosuchfile"
            case 10:
                result.answer = "parsererror"
            case 11:
                result.answer = "timeout"
            case 12:
                result.answer = "memout"
            case _:
                result.answer = get_status_from_output(result)
        if options.args().statistics and not parse_stats(result):
            logging.warn(f"Parsing statistics failed for {result.stdout}")
