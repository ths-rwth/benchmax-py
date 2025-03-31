import logging
import re

from .. import options
from ..results.Result import Result
from .Tool import Tool


def get_status_from_output(result: Result) -> str:
    if "GNU MP: Cannot allocate memory" in result.stderr:
        return "memout"
    if "Minisat::OutOfMemoryException" in result.stderr:
        return "memout"
    return "segfault"


def parse_stats(result: Result) -> bool:
    raw_output = result.stdout
    i = raw_output.find("(:")
    if i < 0:
        return True

    r_category = re.compile(
        r"\(:(?P<prefix>\S+)\s+\(\s*(?P<values>(?::\S+\s+\S*\s*)+)(?P<tail>\)\s*\)\s*)"
    )

    r_values = re.compile(r":(?P<key>\S+)\s+(?P<val>[^\s):]+)")

    logging.debug("trying to find stats")
    m = re.match(r_category, raw_output[i:])
    if m is None:
        return False
    logging.debug("got a match")

    while m != None:
        values = re.finditer(r_values, m.group("values"))
        for v in values:
            result.additional_info[m.group("prefix") + "_" + v.group("key")] = v.group(
                "val"
            )
        i += m.end()
        m = re.match(r_category, raw_output[i:])
    logging.debug("processed all submatches")

    return True


class SMTRAT(Tool):
    def __init__(self, command: str, name="SMTRAT"):
        super().__init__(command, name=name)

    def get_command_line(self, file: str) -> str:
        res = self.binary + " " + self.arguments
        if options.args().statistics:
            res += " --stats.print"
        return res + " " + file

    def can_handle(self, file: str) -> bool:
        return file.endswith(".smt2")

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
            if result.answer in ["sat", "unsat", "unknown", "wrong", "success"]:
                logging.warning(f"Parsing statistics failed for {result.stdout}")


class SMTRAT_QE(SMTRAT):
    def __init__(self, command: str):
        super().__init__(command, "SMTRAT_QE")

    def parse_additional(self, result: Result):
        m = re.search("Equivalent Quantifier-Free Formula:[^\n]*\n", result.stdout)
        if m is not None:
            result.stdout = result.stdout[m.end() :]
        super().parse_additional(result)
        if m is not None:
            result.answer = "success"
