import glob
import logging
import os.path

import options
from jobs import Jobs
from backends.local import local
from backends.slurm import slurm
from BenchmaxException import BenchmaxException


def setup_logging():
    lvl = options.args().logging_level
    if lvl is None: lvl = logging.INFO
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
    logging.debug("Given tools: " + str(tools))

    if len(tools) == 1:
            options.args().common_tool_prefix = os.path.dirname(tools[0].binary)
    else:
        options.args().common_tool_prefix = os.path.commonpath([t.binary for t in tools])
    
    # gather input files
    files = sum(
        [[f for f in glob.glob(dir+"**", recursive=True) if os.path.isfile(f)] for dir in options.args().input_directories ], []
    )
    if len(files) == 0:
        raise BenchmaxException("No input files found!")
    logging.debug("Number of input files: " + str(len(files)))

    options.args().common_file_prefix = os.path.commonpath([dir for dir in options.args().input_directories])
    
    # create jobs
    jobs = Jobs(tools, files)
    if len(jobs) == 0:
        raise BenchmaxException("No valid input found for the given tools!")
    logging.debug("Number of jobs: " + str(len(jobs)))

    match options.args().backend:
        case "local":
            local(jobs)
        case "slurm":
            slurm(jobs)
        case "ssh":
            pass # TODO: do stuff
    