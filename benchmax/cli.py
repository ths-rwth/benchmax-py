import glob
import logging
import os.path

import options
from benchmarks import Benchmarks
from backends.local import local
from backends.slurm import slurm
from BenchmaxException import BenchmaxException


def setup_logging():
    lvl = options.args().logging_level
    if lvl is None:
        lvl = logging.INFO
    logging.basicConfig(format="[benchmax][%(levelname)s] %(message)s", level=lvl)


def benchmax_main():
    setup_logging()

    if options.args().settings:
        print(options.args())
        return

    # gather tools
    if options.args().tools is None:
        raise BenchmaxException("No tools specified!")

    tools = [t for t in options.args().tools if t.is_executable()]
    if len(tools) == 0:
        raise BenchmaxException("No usable tools found!")
    logging.info(f"{len(tools)} tools given")
    logging.debug(str(tools))

    if len(tools) == 1:
        options.args().common_tool_prefix = os.path.dirname(tools[0].binary)
    else:
        options.args().common_tool_prefix = os.path.commonpath(
            [t.binary for t in tools]
        )
    if options.args().common_tool_prefix != "":
        options.args().common_tool_prefix += "/"

    # gather input files
    logging.info("collecting input files")
    files = sum(
        [
            [
                f
                for f in glob.glob(os.path.normpath(dir) + "/**", recursive=True)
                if os.path.isfile(f)
            ]
            for dir in options.args().input_directories
        ],
        [],
    )
    if len(files) == 0:
        raise BenchmaxException("No input files found!")
    logging.info(f"number of collected input files: {len(files)}")

    options.args().common_file_prefix = (
        os.path.commonpath([dir for dir in options.args().input_directories]) + "/"
    )

    # create benchmarking pairs
    benchmarks = Benchmarks(tools, files)
    if len(benchmarks) == 0:
        raise BenchmaxException("no valid input found for the given tools!")
    logging.debug(f"number of tool-input pairings: {len(benchmarks)}")

    match options.args().backend:
        case "local":
            local(benchmarks)
        case "slurm":
            slurm(benchmarks)
        case "ssh":
            pass  # TODO: do stuff

    logging.info("done.")
