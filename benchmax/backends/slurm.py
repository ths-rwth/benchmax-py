from dataclasses import dataclass
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import glob
import logging
import math
import multiprocessing
import os
from pathlib import Path
import re
import time
from tqdm import tqdm

from .backends import *
from ..BenchmaxException import BenchmaxException
from ..benchmarks import Benchmarks
from .. import options


def generate_jobs_file(filename: str, benchmarks: Benchmarks):
    logging.info("writing slurm jobs file to " + filename)
    with open(filename, "w+") as f:
        f.writelines(
            [tool.get_command_line(file) + "\n" for tool, file in benchmarks.pairs]
        )


@dataclass
class ChunkArgs:
    file_suffix: str
    filename_joblist: str
    tmp_dir: str
    limit_time: timedelta
    grace_time: timedelta
    limit_mem_kb: int  # TODO memory type?
    array_size: int
    slice_size: int
    n_tasks: int


def generate_submit_file_chunked(args: ChunkArgs) -> str:
    filename = f"{args.tmp_dir}/job-{args.file_suffix}.job"
    logging.info(f"generating submit file {filename}")

    # rough estimation of required time
    timeout = options.args().timeout + options.args().gracetime
    minutes = args.slice_size * timeout / 30
    estimate = int(min(minutes + 1, 60 * 24))

    with open(filename, "w+") as f:
        f.writelines(
            [
                # shebang
                "#!/usr/bin/env zsh\n",
                # job name
                "### Job name\n",
                "#SBATCH --job-name=benchmax\n",
                # output files
                "#SBATCH -o " + args.tmp_dir + "/JOB.%A_%a.out\n",
                "#SBATCH -e " + args.tmp_dir + "/JOB.%A_%a.err\n",
                # required time
                "#SBATCH -t " + str(estimate) + "\n",
                # memory usage
                "#SBATCH --mem-per-cpu ",
                str(math.ceil(args.limit_mem_kb / 1000) + 1024) + "M\n",
                # load environment
                "source " + options.args().slurm_env + "\n",
                # change dir
                "cd " + args.tmp_dir + "\n",
                # calculate slices
                "min=$SLURM_ARRAY_TASK_MIN\n",
                "max=$SLURM_ARRAY_TASK_MAX\n",
                "cur=$SLURM_ARRAY_TASK_ID\n",
                "slicesize=" + str(args.slice_size) + "\n",
                f"start=$(( (cur - 1) * slicesize + 1 ))\n",
                f"end=$(( start + slicesize - 1 ))\n",
                f"end=$(( end<{args.n_tasks} ? end : {args.n_tasks}))\n",
                # Execute this slice
                "for i in `seq ${start} ${end}`; do\n",
                "lineidx=$(( i ))\n",
                '\tcmd=$(time sed -n "${lineidx}p" < ' + args.filename_joblist + ")\n",
                '\techo "Executing $cmd"\n',
                '\techo "# START ${i} #"\n',
                '\techo "# START ${i} #" >&2\n',
                '\tstart=`date +"%s%3N"`\n',
                "\tulimit -c 0 && ulimit -S -v " + str(args.limit_mem_kb),
                " && eval /usr/bin/time -v timeout --signal=TERM",
                " --preserve-status " + str(timeout) + "s  $cmd ; rc=$?" + "\n",
                '\tend=`date +"%s%3N"`\n',
                '\techo "# END ${i} #"\n',
                '\techo "# END ${i} #" 1>&2\n',
                '\techo "time: $(( end - start ))"\n',
                '\techo "exitcode: $rc"\n',
                '\techo "# END DATA ${i} #"\n',
                "done\n",
            ]
        )
    return filename


def run_job(jobs: Benchmarks, array_size: int, slice_size: int) -> int:
    jobs_filename = (
        f"{options.args().slurm_tmp_dir}/jobs-{options.args().start_time}.jobs"
    )

    generate_jobs_file(jobs_filename, jobs)

    submitfile = generate_submit_file_chunked(
        ChunkArgs(
            str(options.args().start_time),
            jobs_filename,
            options.args().slurm_tmp_dir,
            options.args().timeout,
            options.args().gracetime,
            options.args().memout,
            array_size,
            slice_size,
            len(jobs),
        )
    )

    logging.info("submitting job now")

    res = call_program(
        f"sbatch --array=1-{array_size} "
        + options.args().slurm_sbatch_options
        + " "
        + submitfile
    )
    # TODO: what if slurm does not work at all?

    job_id = re.search("Submitted batch job ([0-9]+)", res.stdout)
    if job_id is None:
        raise BenchmaxException(
            "unable to obtain job id from slurm output: " + str(res.stdout)
        )
    return int(job_id.group(1))


def parse_chunk(jobs: Benchmarks, out_file: str, results: Results):
    logging.debug(f"Processing file {out_file}")
    with open(out_file, "r") as f:
        content_out = f.read()
    with open(out_file.replace(".out", ".err"), "r") as f:
        content_err = f.read()

    pattern_out = re.compile(
        r"Executing (.+)\n# START ([0-9]+) #([\s\S]*)# END \2 #(?:([\s\S]*)# END DATA \2 #)?"
    )
    pattern_err = re.compile(
        r"# START ([0-9]+) #([\s\S]*)# END \1 #(?:([\s\S]*)# END DATA \1 #)?"
    )

    for m_out, m_err in zip(
        pattern_out.finditer(content_out), pattern_err.finditer(content_err)
    ):
        res = Result()

        # gather tool and file from command
        cmd = m_out.group(1)
        logging.debug(f"Processing command {cmd}")
        tool_found = False
        for tool in jobs.tools:
            p = tool.parse_command_line(cmd)
            if p is not None:
                used_tool = tool
                used_input = p
                tool_found = True
                break
        if not tool_found:
            logging.warning(f"could not find tool for {cmd} from {out_file}")

        # output
        res.stdout = m_out.group(3)

        # exitcode
        match_e = re.search("exitcode: (.*)", m_out.group(4))
        if match_e is None:
            logging.warning(f"did not find exitcode in {m_out.group(4)}")
        else:
            res.exit_code = int(match_e.group(1))

        # runtime
        match_t = re.search("time: (.*)", m_out.group(4))
        if match_t is None:
            logging.warning(f"did not find time in {m_out.group(4)}")
        else:
            res.runtime = timedelta(milliseconds=int(match_t.group(1)))

        res.stderr = m_err.group(2)
        res.peak_memory_kbytes = parse_peak_memory(res.stderr)

        tool.parse_additional(res)
        sanitize_result(used_tool, used_input, res)
        res.stdout = ""
        res.stderr = ""
        results.add_result(used_tool, used_input, res)


def job_finished(job_id: int) -> bool:
    finished_states = ["COMPLETED", "CANCELLED", "TIMEOUT"]
    cmd = "sacct --noheader -o state  -j " + str(job_id)
    output = call_program(cmd)
    for line in output.stdout.splitlines():
        if len(line) <= 1:
            continue
        if not any([state in line for state in finished_states]):
            return False
    return True


def monitor_progress(total_tasks: int, job_id: int):
    update_period_s = 30

    p1 = tqdm(
        total=total_tasks,
        position=0,
        desc="Started  tasks",
        ncols=100,
        dynamic_ncols=True,
    )
    p2 = tqdm(
        total=total_tasks,
        position=1,
        desc="Finished tasks",
        ncols=100,
        dynamic_ncols=True,
    )
    p3 = tqdm(
        total=10 * update_period_s,
        position=2,
        desc="   Next update",
        ncols=100,
        dynamic_ncols=True,
    )
    current_finished = 0
    current_started = 0
    with p1 as pbar_started, p2 as pbar_finished, p3 as pbar_countdown:
        while current_finished < total_tasks:
            # give the server some rest before the next request
            for _ in range(10 * update_period_s):
                pbar_countdown.update(1)
                time.sleep(0.1)

            logging.debug("\n\n\nquerying slurm about running/pending tasks")
            # check queue for running and pending tasks belonging to the jobs
            req = "squeue --noheader --array --states=PD,R"
            req += " --format=%t"
            req += " --jobs=" + str(job_id)
            logging.debug(req)
            response = call_program(req)  # TODO: what if it does not work?
            # count running and pending tasks
            pending = response.stdout.count("PD")
            running = response.stdout.count("R")
            logging.debug("pending: " + str(pending))
            logging.debug("running: " + str(running))
            new_started = total_tasks - pending
            new_finished = total_tasks - pending - running
            pbar_started.update(new_started - current_started)
            pbar_finished.update(new_finished - current_finished)
            current_started = new_started
            current_finished = new_finished

            # if all tasks are finished (despite different counts), exit loop
            if job_finished(job_id):
                logging.debug("array job finished according to sacct")
                pbar_started.update(total_tasks - current_started)
                pbar_finished.update(total_tasks - current_finished)
                break

            # reset "spinner"
            pbar_countdown.update(-10 * update_period_s)


def cancel_job(job_id: int):
    call_program("scancel " + str(job_id))


def slurm(benchmarks: Benchmarks):
    tmp_dir = str(os.path.normpath(options.args().slurm_tmp_dir))
    Path(tmp_dir).mkdir(parents=True, exist_ok=True)

    if not options.args().only_collect:
        logging.info(f"clear directory for temporary results ({tmp_dir})")
        for f in glob.glob(tmp_dir + "/*"):
            os.remove(f)

        try:
            # submit job
            array_size = min(len(benchmarks), options.args().slurm_array_size)
            slice_size = math.ceil(len(benchmarks) / array_size)
            array_size = math.ceil(len(benchmarks) / slice_size)
            job_id = run_job(benchmarks, array_size, slice_size)
            logging.info(f"job {job_id} scheduled.")

            # continuously check status
            monitor_progress(array_size, job_id)
        except:
            logging.error("some exception occurred, will cancel slurm jobs")
            cancel_job(job_id)
            raise
    else:
        logging.info("only collecting results.")

    # collect jobs
    logging.info("collecting results")
    out_files = glob.glob(tmp_dir + "/JOB.*.out")
    for f in out_files:
        if not os.path.exists(f.replace(".out", ".err")):
            raise BenchmaxException(f"missing corresponding err file for {f}")

    logging.info(f"collected {len(out_files)} out files")

    results = Results()

    for f in tqdm(out_files, desc="parsing results", ncols=100, dynamic_ncols=True):
        parse_chunk(benchmarks, f, results)

    # finalize
    check_for_missing_results(benchmarks, results)
    write_results(benchmarks, results)

    if options.args().slurm_archive_logs is not None:
        dirname = options.args().slurm_tmp_dir
        archive = options.args().slurm_archive_logs
        archive += "-" + str(options.args().start_time) + ".tgz"

        output = call_program(
            f"tar --force-local -czf {archive} -C {dirname} `ls {dirname}`"
        )
        if output.returncode == 0:
            logging.info(f"archived log files in {archive} from {dirname}")
        else:
            logging.warning("archiving log files failed!")
            logging.warning(output.stdout)

    if not options.args().slurm_keep_logs:
        logging.info("deleting log files directory for temporary results")
        for f in out_files:
            if os.path.exists(f):
                os.remove(f)
            if os.path.exists(f.replace(".out", ".err")):
                os.remove(f.replace(".out", ".err"))
