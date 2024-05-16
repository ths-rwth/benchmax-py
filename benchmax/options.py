import argparse
import datetime as dt
import logging
import re
import sys

from .backends.backends import add_backend_options
from .tools.tools import add_tool_options


def parse_timeout(time_str: str) -> int:
    regex = re.compile(r"((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?")
    parts = regex.match(time_str)
    if not parts:
        raise argparse.ArgumentError("Invalid format for timeout!")
    parts = parts.groupdict()
    time_params = {}
    for name, param in parts.items():
        if param:
            time_params[name] = int(param)
    return int(dt.timedelta(**time_params).total_seconds())


def parse_memout(mem_str: str) -> int:
    regex = re.compile(r"([0-9]+)([KMG])i?")
    parts = regex.fullmatch(mem_str)
    if not parts:
        raise argparse.ArgumentError("Invalid format for memout!")
    match parts.group(2):
        case "K":
            return int(parts.group(1))
        case "M":
            return int(parts.group(1)) * 1000
        case "G":
            return int(parts.group(1)) * 1000_000


def positive_int(numeric_str: str) -> int:
    res = int(numeric_str)
    if res < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return res


def parse_options(cmdlineoptions=None):
    ap = argparse.ArgumentParser(
        prog="benchmax",
        description="Automated benchmarking for multiple tools.",
        epilog="For further information, consult the documentation at https://git.rwth-aachen.de/ths/smt/benchmax-py",
    )

    ap.add_argument("--settings", help="show used settings", action="store_true")
    ap.add_argument(
        "--verbose",
        help="show detailed output",
        dest="logging_level",
        action="store_const",
        const=logging.DEBUG,
    )
    ap.add_argument(
        "--quiet",
        help="show only most important output",
        dest="logging_level",
        action="store_const",
        const=logging.WARNING,
    )

    # TODO: version

    ap.add_argument(
        "--config", help="load options from config file", dest="config", metavar="FILE"
    )

    # Output Settings
    output_group = ap.add_argument_group("output options")

    output_group.add_argument(
        "-X",
        "--output-xml",
        help="filename for xml output file. "
        + "Used as common prefix if split-output is enabled",
        metavar="FILE",
        dest="xml_file",
    )
    output_group.add_argument(
        "-C",
        "--output-csv",
        help="filename for csv output file. "
        + "Used as common prefix if split-output is enabled",
        metavar="FILE",
        dest="csv_file",
    )
    output_group.add_argument(
        "--split-output",
        help="split output data into one file per tool",
        action="store_true",
        dest="split_output",
    )
    output_group.add_argument(
        "-s", "--statistics", help="collect statistics if possible", action="store_true"
    )

    # Benchmark Settings
    benchmark_group = ap.add_argument_group("benchmark options")

    benchmark_group.add_argument(
        "-M",
        "--memout",
        help="memory limit per benchmark instance; unit must be one of "
        + "K, Ki (Kiwibytes), M, Mi (Miwibytes), G, Gi (Giwibytes).",
        metavar="<number><unit>",
        type=parse_memout,
        required=True,
    )
    benchmark_group.add_argument(
        "-T",
        "--timeout",
        help="time limit per benchmark instance",
        metavar="[<hours>h][<minutes>m][<seconds>s]",
        type=parse_timeout,
        required=True,
    )
    benchmark_group.add_argument(
        "--gracetime",
        help="grace time (in seconds) added to the timeout",
        metavar="seconds",
        type=positive_int,
        default=3,
    )
    benchmark_group.add_argument(
        "-D",
        "--directory",
        help="path(s) to a directory containing input files",
        required=True,
        metavar="DIR",
        dest="input_directories",
        nargs="+",
    )

    add_backend_options(ap)
    add_tool_options(ap)

    if cmdlineoptions is None:
        cmdlineoptions = sys.argv[1:]

    for i in range(len(cmdlineoptions)):
        if cmdlineoptions[i] == "--config":
            if i + 1 < len(cmdlineoptions):
                file = cmdlineoptions[i + 1]
                with open(file) as f:
                    import shlex

                    opts = shlex.split(f.read().replace("\n", " "))
                    cmdlineoptions += opts
                break

    res = ap.parse_args(cmdlineoptions)

    res.start_time = int(dt.datetime.now().timestamp())

    return res


__PARSED_ARGS = None


def args(cmdlineoptions=None):
    global __PARSED_ARGS
    if __PARSED_ARGS is None:
        __PARSED_ARGS = parse_options()
    return __PARSED_ARGS
