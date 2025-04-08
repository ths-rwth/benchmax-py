import csv
from datetime import timedelta
import logging
import os.path
from pathlib import Path

from ..benchmarks import Benchmarks
from ..results.Results import Results
from ..tools.Tool import Tool
from .. import options


def write_results_csv(
    benchmarks: Benchmarks,
    results: Results,
    filename: str,
    tools: list[Tool] | None = None,
):
    if tools is None:
        tools = benchmarks.tools

    # header: solvers and stats in two rows
    columns_dict = {t: set() for t in tools}

    for t, f in benchmarks.pairs:
        if t in tools:
            r = results.get(t, f)
            if r is None:
                continue
            for s in r.additional_info:
                columns_dict[t].add(s)

    first_row = [""]
    second_row = [""]
    for t in columns_dict:
        first_row += [t.binary.removeprefix(options.args().common_tool_prefix)] * (
            4 + len(columns_dict[t])
        )
        second_row += ["runtime", "peak_memory_kbytes", "answer", "exitcode"]
        second_row += list(columns_dict[t])

    # write the actual results
    logging.info("writing results to " + str(filename))
    with open(filename, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows([first_row, second_row])

        for f in benchmarks.files:
            row = [f.removeprefix(options.args().common_file_prefix)]
            for t in columns_dict:
                result = results.get(t, f)
                if result is None:
                    row += [None] * (4 + len(columns_dict[t]))
                else:
                    row += [
                        int(result.runtime / timedelta(milliseconds=1)),
                        int(result.peak_memory_kbytes),
                        str(result.answer),
                        int(result.exit_code),
                    ] + [result.additional_info.get(s, None) for s in columns_dict[t]]
            writer.writerow(row)


def write_csv_for_each_tool(benchmarks: Benchmarks, results: Results, file_prefix: str):
    for t in benchmarks.tools:
        filename = (
            file_prefix
            + "_"
            + t.binary.removeprefix(options.args().common_tool_prefix).replace("/", "_")
        )
        count = 1
        if os.path.isfile(filename + ".csv"):
            while os.path.isfile(filename + str(count) + ".csv"):
                count += 1
            filename = filename + str(count) + ".csv"
        else:
            filename = filename + ".csv"
        Path(filename).parents[0].mkdir(parents=True, exist_ok=True)
        logging.info("writing file " + filename)
        write_results_csv(benchmarks, results, filename, [t])
