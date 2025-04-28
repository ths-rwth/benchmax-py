import argparse
from .Tool import Tool
from .SMTRAT import SMTRAT, SMTRAT_QE
from .Z3 import Z3, Z3_QE
from .Redlog import Redlog
from .CDD import CDD
from .cvc5 import cvc5


def add_tool_options(parser: argparse.ArgumentParser):
    tool_group = parser.add_argument_group("tool options")

    tool_group.add_argument(
        "--tool",
        help="A generic tool to evaluate",
        dest="tools",
        metavar="PATH",
        type=Tool,
        action="append",
    )

    tool_group.add_argument(
        "-S",
        "--smtrat",
        help="An SMT-RAT tool with SMT-Lib interface",
        dest="tools",
        metavar="PATH",
        type=SMTRAT,
        action="append",
    )

    tool_group.add_argument(
        "-Q",
        "--smtrat-qe",
        help="An SMT-RAT quantifier elimination tool with SMT-Lib interface",
        dest="tools",
        metavar="PATH",
        type=SMTRAT_QE,
        action="append",
    )

    tool_group.add_argument(
        "-Z",
        "--z3",
        help="z3 with SMT-Lib interface",
        dest="tools",
        metavar="PATH",
        type=Z3,
        action="append",
    )

    tool_group.add_argument(
        "--z3-qe",
        help="z3 for linear quantifier elimination with SMT-Lib interface",
        dest="tools",
        metavar="PATH",
        type=Z3_QE,
        action="append",
    )

    tool_group.add_argument(
        "--redlog",
        help="redlog quantifier elimination",
        dest="tools",
        metavar="PATH",
        type=Redlog,
        action="append",
    )

    tool_group.add_argument(
        "--cdd",
        help="CDD polyhedron projection",
        dest="tools",
        metavar="PATH",
        type=CDD,
        action="append",
    )

    tool_group.add_argument(
        "--cvc5",
        help="cvc5 with SMT-Lib interface",
        dest="tools",
        metavar="PATH",
        type=cvc5,
        action="append",
    )

