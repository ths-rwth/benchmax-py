from datetime import timedelta
from tqdm import tqdm
from timeit import default_timer

from .backends import *
from ..benchmarks import Benchmarks
from .. import options
from ..results.Result import Result
from ..results.Results import Results
from ..tools.Tool import Tool


def process(tool: Tool, file: str, results: Results):
    # prepare command
    call: str = ""
    call += "ulimit -S -t " + str(options.args().timeout) + " && "
    call += "ulimit -S -v " + str(options.args().memout) + " && "
    call += "/usr/bin/time -v "
    call += tool.get_command_line(file)

    # call and time command
    start = default_timer()
    out = call_program(call)
    end = default_timer()

    # extract result information
    result = Result()
    result.runtime = timedelta(seconds=(end - start))
    result.exit_code = out.returncode
    result.stdout = out.stdout
    result.stderr = out.stderr
    result.peak_memory_kbytes = parse_peak_memory(result.stderr)
    tool.parse_additional(result)
    sanitize_result(tool, file, result)
    results.add_result(tool, file, result)


def local(benchmarks: Benchmarks):
    results = Results()

    # TODO: multiprocessing?
    # if we write the result immediately, this could work without sharing to much data
    # Or write the output into single files like with slurm
    for tool, file in tqdm(
        benchmarks.pairs, total=len(benchmarks.pairs), dynamic_ncols=True
    ):
        process(tool, file, results)

    check_for_missing_results(benchmarks, results)
    write_results(benchmarks, results)
