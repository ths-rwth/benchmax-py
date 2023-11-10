import argparse
from tools.Tool import Tool
from tools.SMTRAT import SMTRAT, SMTRAT_QE
from tools.Z3 import Z3, Z3_QE


def add_tool_options(parser: argparse.ArgumentParser):
    tool_group = parser.add_argument_group("Tool options")

    tool_group.add_argument(
        "--tool",
        help="A generic tool to evaluate",
        dest="tools",
        metavar="path",
        type=Tool,
        action="append",
    )

    tool_group.add_argument(
        "-S",
        "--smtrat",
        help="An SMT-RAT tool with SMT-Lib interface",
        dest="tools",
        metavar="path",
        type=SMTRAT,
        action="append",
    )

    tool_group.add_argument(
        "-Q",
        "--smtrat-qe",
        help="An SMT-RAT quantifier elimination tool with SMT-Lib interface",
        dest="tools",
        metavar="path",
        type=SMTRAT_QE,
        action="append",
    )

    tool_group.add_argument(
        "-Z",
        "--z3",
        help="z3 with SMT-Lib interface",
        dest="tools",
        metavar="path",
        type=Z3,
        action="append",
    )

    tool_group.add_argument(
        "--z3-qe",
        help="z3 for linear quantifier elimination with SMT-Lib interface",
        dest="tools",
        metavar="path",
        type=Z3_QE,
        action="append",
    )
