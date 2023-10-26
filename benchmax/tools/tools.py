import argparse
from .Tool import Tool
from .SMTRAT import SMTRAT

def add_tool_options(parser: argparse.ArgumentParser):
    tool_group = parser.add_argument_group("Tool options")

    tool_group.add_argument(
        "--tool",
        help="A generic tool to evaluate",
        dest="tools",
        metavar="path",
        type=Tool,
        action="append"
    )

    tool_group.add_argument(
        "-S","--smtrat",
        help="An SMT-RAT tool with SMT-Lib interface",
        dest="tools",
        metavar="path",
        type=SMTRAT,
        action="append"
    )