import argparse
import logging
import re
import subprocess

from jobs import Jobs
import options
from results.Results import Results
from results.Result import Result
from results.XMLWriter import XMLWriter
from tools.Tool import Tool


def add_backend_options(parser: argparse.ArgumentParser):
    backend_group = parser.add_argument_group("Backend options")

    backend_group.add_argument(
        "-b","--backend",
        help="Backend to use for running the benchmarks",
        required=True,
        dest="backend",
        choices=["local","slurm","ssh"]
    )

    # Local Backend Settings
    # Nothing here so far

    # Slurm Backend Settings
    backend_group.add_argument(
        "--slurm.tmp-dir",
        help="directory for storing temporary result files for slurm",
        dest="slurm_tmp_dir",
        metavar="DIR",
    )

    backend_group.add_argument(
        "--slurm.keep-logs",
        help="keep the outputfiles in tmp dir",
        dest="slurm_keep_logs",
        action="store_true"
    )

    backend_group.add_argument(
        "--slurm.archive-logs",
        help="store logs in tgz archive with given prefix",
        dest="slurm_archive_logs",
        metavar="PREFIX",
        type=str,
    )

    backend_group.add_argument(
        "--slurm.array-size",
        help="size of slurm job arrays",
        dest="slurm_array_size",
        metavar="SIZE",
        type=options.positive_int,
    )

    backend_group.add_argument(
        "--slurm.slice-size",
        help="number of benchmarks per slurm array task",
        dest="slurm_slice_size",
        metavar="SIZE",
        type=options.positive_int
    )

    backend_group.add_argument(
        "--slurm.sbatch-options",
        help="additional slurm sbatch options",
        dest="slurm_sbatch_options",
        metavar="OPTIONS",
        type=str
    )

    backend_group.add_argument(
        "--slurm.submit-delay",
        help="delay between job submissions (in milliseconds)",
        dest="slurm_submit_delay",
        metavar="TIME",
        type=options.positive_int,
        default=100
    )

    # SSH Backend Settings
    # TODO


def check_for_missing_results(jobs: Jobs, results: Results):
    for tool, file in jobs.jobs:
        res = results.get(tool, file)
        if not res and tool.can_handle(file):
            logging.warn(f"Missing result for {tool} on {file}")


def sanitize_result(tool : Tool, file: str, result: Result):
    if result.answer == "segfault":
        if result.peak_memory_kbytes > options.args().memout:
            result.answer = "memout"

    timediff = result.runtime.total_seconds() - options.args().timeout
    if timediff > 0:
        result.answer = "timeout"
        result.stderr = ""
        result.stdout = ""
        if timediff > options.args().gracetime:
            logging.warn(f"Running {tool} on {file} exceeded grace time")
            logging.warn(
                "runtime: " + str(result.runtime.total_seconds()) + ", "
                + str(options.args().timeout + options.args().gracetime)
            )
    # TODO: do more, also for memout?


def write_results(jobs: Jobs, results: Results):
    logging.info("Writing results to " + options.args().output_file)
    xml = XMLWriter(options.args().output_file)
    xml.write(jobs, results)
    

def call_program(cmd: str):
    res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True
        )
    return res


def parse_peak_memory(output: str) -> int:
    m = re.search(r"Maximum resident set size \(kbytes\): ([0-9]+)", output)
    if m: return int(m.group(1))
    else:
        logging.warn("Could not extract memory usage from output: " + output)
        return -1 # TODO: avoid magic number
    