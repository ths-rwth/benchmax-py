from dataclasses import dataclass
from datetime import timedelta
import logging
import os.path
from pathlib import Path

from ..benchmarks import Benchmarks
from ..results.Results import Results
from ..results.Result import Result
from ..tools.Tool import Tool
from .. import options


def attr_to_str(attr) -> str:
    t = ""
    for key, value in attr.items():
        t += " " + str(key) + '="' + str(value) + '"'
    return t


class WriteXMLNode:
    def __init__(self, dest, indentation: int, tag: str, **attr):
        self.dest = dest
        self.indentation = indentation
        self.tag = tag
        self.attr = attr

    def __enter__(self):
        self.dest.write("\t" * self.indentation)
        self.dest.write("<" + self.tag + attr_to_str(self.attr) + ">\n")
        return self

    def __exit__(self, exctype, exc_value, traceback):
        self.dest.write(("\t" * self.indentation) + "</" + self.tag + ">\n")

    def write_child(self, tag: str, **attr):
        return WriteXMLNode(self.dest, self.indentation + 1, tag, **attr)

    def write_leaf(self, tag: str, text: str | None = None, **attr):
        self.dest.write("\t" * (self.indentation + 1))
        if text is None:
            self.dest.write("<" + tag + attr_to_str(attr) + " />")
        else:
            self.dest.write(
                "<" + tag + attr_to_str(attr) + ">" + text + "</" + tag + ">"
            )
        self.dest.write("\n")


def sanitize(text: str) -> str:
    return text.replace("<", "&lt;").replace(">", "&gt;")


def sanitize_tool(text: str) -> str:
    return sanitize(text.removeprefix(options.args().common_tool_prefix))


def sanitize_file(text: str) -> str:
    return sanitize(text.removeprefix(options.args().common_file_prefix))


def write_run(parent: WriteXMLNode, tool: Tool, result: Result):
    with parent.write_child("run", solver_id=sanitize_tool(tool.binary)) as run:
        if len(result.additional_info) > 0:
            with run.write_child("statistics") as statistics:
                for key, value in result.additional_info.items():
                    statistics.write_leaf("stat", text=value, name=sanitize(key))

        with run.write_child("results") as resnode:
            resnode.write_leaf(
                "result", text=str(result.answer), name="answer", type="string"
            )
            resnode.write_leaf(
                "result", text=str(result.exit_code), name="exitcode", type="int"
            )
            resnode.write_leaf(
                "result",
                text=str(int(result.runtime / timedelta(milliseconds=1))),
                name="runtime",
                type="milliseconds",
            )
            resnode.write_leaf(
                "result",
                text=str(result.peak_memory_kbytes),
                name="peak_memory",
                type="kbytes",
            )


def write_file_results(
    parent: WriteXMLNode, filename: str, results: Results, tools: list[Tool]
):
    with parent.write_child("file", name=sanitize_file(filename)) as f:
        for tool in tools:
            res = results.get(tool, filename)
            if res is None:
                continue
            write_run(f, tool, res)


def write_results(
    benchmarks: Benchmarks, results: Results, file, tools: list[Tool] | None = None
):
    if tools is None:
        tools = benchmarks.tools
    with WriteXMLNode(file, 0, "results") as root:
        with root.write_child("information") as info:
            info.write_leaf(
                "info",
                name="timeout",
                type="seconds",
                value=str(options.args().timeout),
            )
            info.write_leaf(
                "info", name="memout", type="kbytes", value=str(options.args().memout)
            )

        with root.write_child(
            "solvers", prefix=options.args().common_tool_prefix
        ) as solvers:
            for tool in tools:
                solvers.write_leaf(
                    "solver",
                    solver_id=sanitize_tool(tool.binary),
                    options=tool.arguments,
                )

        with root.write_child("statistics") as statistics:
            for s in results.collect_statistics():
                statistics.write_leaf("stat", name=sanitize(s))

        with root.write_child(
            "benchmarks", prefix=options.args().common_file_prefix
        ) as benchmarks_node:
            for filename in benchmarks.files:
                write_file_results(benchmarks_node, filename, results, tools)


@dataclass
class XMLWriter:
    filename: str

    def write(self, benchmarks: Benchmarks, results: Results):
        Path(self.filename).parents[0].mkdir(parents=True, exist_ok=True)
        logging.info("writing results to " + self.filename)
        with open(self.filename, "w") as file:
            file.write('<?xml version="1.0"?>\n')
            write_results(benchmarks, results, file)

    def write_for_each_tool(self, benchmarks: Benchmarks, results: Results):
        for t in benchmarks.tools:
            filename = (
                self.filename.replace(".xml", "")
                + "_"
                + sanitize_tool(t.binary).replace("/", "_")
            )
            count = 1
            if os.path.isfile(filename + ".xml"):
                while os.path.isfile(filename + str(count) + ".xml"):
                    count += 1
                filename = filename + str(count) + ".xml"
            else:
                filename = filename + ".xml"
            Path(filename).parents[0].mkdir(parents=True, exist_ok=True)
            logging.info("writing results to " + filename)
            with open(filename, "w") as file:
                file.write('<?xml version="1.0"?>')
                write_results(benchmarks, results, file, [t])
