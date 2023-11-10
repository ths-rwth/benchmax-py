import logging
import re
from benchmax.results.Result import Result

import options
from results.Result import Result
from tools.Tool import Tool


class Z3(Tool):
    def __init__(self, command: str):
        super().__init__(command, "Z3")

    def get_command_line(self, file: str) -> str:
        res = self.binary + " " + self.arguments + " " + file
        if options.args().statistics:
            res += " -st"
        return res

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

        # TODO: parse stats?


class Z3_QE(Z3):
    def parse_additional(self, result: Result):
        rex = re.compile(r"\(goals\s*\(goal\s*(.*):precision")
        match_out = rex.search(result.stdout)
        if match_out is None:
            logging.warn("could not parse qe output for " + str(self.binary))
        else:
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
