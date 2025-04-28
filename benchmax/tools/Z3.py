import logging
import re

from .. import options
from ..results.Result import Result
from .Tool import Tool

def parse_stats(result: Result) -> bool:
    raw_output = result.stdout
    i = raw_output.find("(:")
    if i < 0:
        return True

    r_category = re.compile(
        r"\(\s*(?P<values>(?::\S+\s+\S*\s*)+)(?P<tail>\)\s*)"
    )

    r_values = re.compile(r":(?P<key>\S+)\s+(?P<val>[^\s):]+)")

    m = re.match(r_category, raw_output[i:])
    if m is None:
        return False

    while m != None:
        values = re.finditer(r_values, m.group("values"))
        for v in values:
            result.additional_info[v.group("key")] = v.group("val")
        i += m.end()
        m = re.match(r_category, raw_output[i:])

    return True

class Z3(Tool):
    def __init__(self, command: str):
        super().__init__(command, "Z3")

    def get_command_line(self, file: str) -> str:
        res = self.binary + " " + self.arguments
        if options.args().statistics:
            res += " -st"
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

        if options.args().statistics and not parse_stats(result):
            if result.answer in ["sat", "unsat", "unknown", "wrong", "success"]:
                logging.warning(f"Parsing statistics failed for {result.stdout}")


class Z3_QE(Z3):
    def parse_additional(self, result: Result):
        # check whether the output still contains quantifiers
        match_incomplete_goal = re.search(
            r"\(goals\s*\(goal\s*\((?:exists|forall)", result.stdout
        )
        if match_incomplete_goal:
            result.answer = "invalid"
            return

        match_out = re.search(r"\(goals\s*\(goal\s*([\s\S]*):precision", result.stdout)
        if match_out:
            out_formula = match_out.group(1)
            n_constraints = 0
            n_constraints += out_formula.count("(= ")
            n_constraints += out_formula.count("(< ")
            n_constraints += out_formula.count("(> ")
            n_constraints += out_formula.count("(<= ")
            n_constraints += out_formula.count("(>= ")

            result.additional_info["trivial_false"] = "0"
            result.additional_info["trivial_true"] = "0"
            result.additional_info["contains_disjunction"] = "0"
            if n_constraints == 0:
                if "false" in out_formula:
                    result.additional_info["trivial_false"] = "1"
                else:
                    result.additional_info["trivial_true"] = "1"
                result.additional_info["output_constraints"] = "1"
            else:
                result.additional_info["output_constraints"] = str(n_constraints)

            if "(or " in out_formula:
                result.additional_info["contains_disjunction"] = "1"

        super().parse_additional(result)
        if match_out:
            result.answer = "success"
