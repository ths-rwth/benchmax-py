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

from backends.backends import *
from BenchmaxException import BenchmaxException
from jobs import Jobs
import options


def generate_jobs_file(filename: str, range: tuple[int, int], jobs: Jobs):
    logging.info("writing slurm jobs file to " + filename)
    with open(filename, "w+") as f:
        logging.debug("taking jobs " + str(range[0]) + ".." + str(range[1]))
        f.writelines(
            [
                tool.get_command_line(file) + "\n"
                for tool, file in jobs.jobs[range[0] : range[1]]
            ]
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
    job_range: tuple[int, int]


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
                # load environment TODO: this feels hacky? -> pass as option?
                "source " + options.args().slurm_env + "\n",
                # change dir
                "cd " + args.tmp_dir + "\n",
                # calculate slices
                "min=$SLURM_ARRAY_TASK_MIN\n",
                "max=$SLURM_ARRAY_TASK_MAX\n",
                "cur=$SLURM_ARRAY_TASK_ID\n",
                "slicesize=" + str(args.slice_size) + "\n",
                f"start=$(( (cur - 1) * slicesize + 1 + {args.job_range[0]} ))\n",
                f"end=$(( start + slicesize - 1 + {args.job_range[0]} ))\n",
                f"end=$((end<{args.job_range[1]} ? end : {args.job_range[1]}))\n",
                # Execute this slice
                "for i in `seq ${start} ${end}`; do\n",
                "lineidx=$(( i - " + str(args.job_range[0]) + " ))\n",
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


def run_job(args: tuple[int, Jobs, multiprocessing.Lock, list[int]]) -> int:
    n, jobs, submission_mutex, job_ids = args
    jobs_filename = str(options.args().slurm_tmp_dir)
    jobs_filename += f"/jobs-{options.args().start_time}-{n-1}.jobs"
    job_size = options.args().slurm_array_size * options.args().slurm_slice_size
    job_range = (job_size * n, min(job_size * (n + 1), len(jobs)))
    generate_jobs_file(jobs_filename, job_range, jobs)

    submitfile = generate_submit_file_chunked(
        ChunkArgs(
            str(options.args().start_time) + "-" + str(n),
            jobs_filename,
            options.args().slurm_tmp_dir,
            options.args().timeout,
            options.args().gracetime,
            options.args().memout,
            options.args().slurm_array_size,
            options.args().slurm_slice_size,
            job_range,
        )
    )

    logging.info(f"delaying for {options.args().slurm_submit_delay}ms")

    with submission_mutex:
        time.sleep(options.args().slurm_submit_delay / 1000)  # delay is ms

    logging.info("submitting job now")

    cmd = "sbatch --array=1-" + str(options.args().slurm_array_size)
    cmd += " " + options.args().slurm_sbatch_options
    cmd += " " + submitfile

    res = call_program(cmd)  # TODO: what if slurm does not work at all?
    job_id = re.search("Submitted batch job ([0-9]+)", res.stdout)
    if job_id is None:
        raise BenchmaxException("unable to obtain job id from slurm output!")
    job_ids.append(int(job_id.group(1)))


def parse_out_file(jobs: Jobs, out_file: str, id_to_data):
    with open(out_file, "r") as f:
        content_out = f.read()

    pattern = re.compile(
        r"Executing (.+)\n# START ([0-9]+) #([^#]*)# END \2 #(?:([^#]*)# END DATA \2 #)?"
    )

    for m in pattern.finditer(content_out):
        res = Result()

        # gather tool and file from command
        cmd = m.group(1)
        tool_found = False
        for tool in jobs.tools:
            p = tool.parse_command_line(cmd)
            if p is not None:
                used_tool = tool
                used_input = p
                tool_found = True
                break
        if not tool_found:
            logging.warn(f"could not find tool for {cmd} from {out_file}")

        # output
        res.stdout = m.group(3)

        # exitcode
        match_e = re.search("exitcode: (.*)", m.group(4))
        if match_e is None:
            logging.warn(f"did not find exitcode in {m.group(4)}")
        else:
            res.exit_code = int(match_e.group(1))

        # runtime
        match_t = re.search("time: (.*)", m.group(4))
        if match_t is None:
            logging.warn(f"did not find time in {m.group(4)}")
        else:
            res.runtime = timedelta(milliseconds=int(match_t.group(1)))

        # update data
        job_id = int(m.group(2)) - 1
        id_to_data[job_id] = used_tool, used_input, res


def parse_err_file(err_file: str, id_to_data):
    with open(err_file, "r") as f:
        content_err = f.read()

    pattern_err = re.compile(
        r"# START ([0-9]+) #([^#]*)# END \1 #(?:([^#]*)# END DATA \1 #)?"
    )

    for m in pattern_err.finditer(content_err):
        data = id_to_data.get(int(m.group(1)) - 1, None)
        if data is None:
            logging.warn(f"no corresponding result for err file {err_file}")
            return
        _, _, res = data
        res.stderr = m.group(2)
        res.peak_memory_kbytes = parse_peak_memory(res.stderr)


def all_jobs_finished(job_ids: list[int]) -> bool:
    finished_states = ["COMPLETED", "CANCELLED", "TIMEOUT"]
    for i in job_ids:
        cmd = "sacct --noheader -o state  -j " + str(i)
        output = call_program(cmd)
        for line in output.stdout.splitlines():
            if len(line) <= 1:
                continue
            if not any([state in line for state in finished_states]):
                return False
    return True


def monitor_progress(total_tasks: int, job_ids: list[int]):
    update_period_s = 30

    p1 = tqdm(total=total_tasks, position=0, desc="Started  tasks", ncols=120)
    p2 = tqdm(total=total_tasks, position=1, desc="Finished tasks", ncols=120)
    p3 = tqdm(total=10 * update_period_s, position=2, desc="   Next update", ncols=120)
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
            req += " --jobs=" + ",".join([str(i) for i in job_ids]) + ""
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

            # if all jobs are finished (despite different counts), exit loop
            if all_jobs_finished(job_ids):
                logging.debug("all jobs finished according to sacct")
                pbar_started.update(total_tasks - current_started)
                pbar_finished.update(total_tasks - current_finished)
                break

            # reset "spinner"
            pbar_countdown.update(-10 * update_period_s)


def cancel_jobs(job_ids: list[int]):
    for i in job_ids:
        call_program("scancel " + str(i))


def slurm(jobs: Jobs):
    tmp_dir = str(os.path.normpath(options.args().slurm_tmp_dir))
    Path(tmp_dir).mkdir(parents=True, exist_ok=True)

    logging.info(f"clear directory for temporary results ({tmp_dir})")
    for f in glob.glob(tmp_dir + "/*"):
        os.remove(f)

    # submit jobs
    jobs_per_batch = options.args().slurm_array_size * options.args().slurm_slice_size
    count = math.ceil(len(jobs) / (jobs_per_batch))
    logging.info(f"creating {count} slurm job(s)")

    submission_mutex = multiprocessing.Lock()

    job_ids = []

    try:
        with ThreadPoolExecutor(max_workers=min(count, 8)) as executor:
            list(
                executor.map(
                    run_job,
                    [(i, jobs, submission_mutex, job_ids) for i in range(count)],
                )
            )

        logging.info("all jobs scheduled.")

        # continuously check status
        logging.info("will try to track progress after 5 seconds")
        time.sleep(5)
        total_tasks = count * options.args().slurm_array_size
        monitor_progress(total_tasks, job_ids)
    except:
        logging.error("some exception occurred, will cancel slurm jobs")
        cancel_jobs(job_ids)
        raise

    # collect jobs
    logging.info("collecting results")
    out_files = glob.glob(tmp_dir + "/JOB.*.out")
    err_files = glob.glob(tmp_dir + "/JOB.*.err")
    logging.info(f"collected {len(out_files)} out, {len(err_files)} err files")
    if len(out_files) != len(err_files):
        logging.warn("number of out and err files differ!")

    id_to_data = {}

    logging.info("parsing results")
    for f in out_files:
        parse_out_file(jobs, f, id_to_data)
    for f in err_files:
        parse_err_file(f, id_to_data)

    results = Results()
    for tool, file, result in tqdm(
        id_to_data.values(), desc="gathering data", ncols=120
    ):
        tool.parse_additional(result)
        sanitize_result(tool, file, result)
        results.add_result(tool, file, result)

    # finalize
    check_for_missing_results(jobs, results)
    write_results(jobs, results)

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
            logging.warn("archiving log files failed!")
            logging.warn(output.stdout)

    if not options.args().slurm_keep_logs:
        logging.info("deleting log files directory for temporary results")
        for f in out_files + err_files:
            if os.path.exists(f):
                os.remove(f)
