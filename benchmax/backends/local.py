from datetime import timedelta
from tqdm import tqdm
from timeit import default_timer

from backends.backends import *
from jobs import Jobs
import options
from results.Result import Result
from results.Results import Results
from tools.Tool import Tool


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


def local(jobs: Jobs):
    results = Results()

    # TODO: multiprocessing?
    for tool, file in tqdm(jobs.jobs, total=len(jobs.jobs)):
        process(tool, file, results)

    check_for_missing_results(jobs, results)
    write_results(jobs, results)
