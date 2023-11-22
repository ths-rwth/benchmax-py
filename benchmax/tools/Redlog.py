from results.Result import Result
from tools.Tool import Tool
import options


class Redlog(Tool):
    def __init__(self, command: str):
        super().__init__(command, "Redlog")

    def can_handle(self, file: str) -> bool:
        return file.endswith(".red")

    def get_command_line(self, file: str) -> str:
        return (
            self.binary
            + " "
            + self.arguments
            + " -k "
            + str(int(options.args().memout / 2))
            + "K "
            + file
        )

    def parse_additional(self, result: Result):
        if result.exit_code != 0:
            result.answer = "invalid"
        else:
            n_constraints = 0
            n_constraints += result.stdout.count(" = ")
            n_constraints += result.stdout.count(" < ")
            n_constraints += result.stdout.count(" > ")
            n_constraints += result.stdout.count(" <= ")
            n_constraints += result.stdout.count(" >= ")

            result.additional_info["trivial_false"] = "0"
            result.additional_info["trivial_true"] = "0"
            result.additional_info["contains_disjunction"] = "0"
            if n_constraints == 0:
                if "false" in result.stdout:
                    result.additional_info["trivial_false"] = "1"
                else:
                    result.additional_info["trivial_true"] = "1"
                result.additional_info["output_constraints"] = "1"
            else:
                result.additional_info["output_constraints"] = str(n_constraints)

            if " or " in result.stdout:
                result.additional_info["contains_disjunction"] = "1"

            result.answer = "success"
