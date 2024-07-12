# Benchmax: an automated benchmarking utility

This is work in progress. For questions, contact Valentin (promies at cs dot rwth-aachen.de).

Benchmax is a tool for automated benchmarking, mainly aimed at SMT solvers, though it can be used for evaluating other tools as well.

Its fundamental model is to load a list of tools and a list of benchmarks, run every tool with every benchmark, obtain the results, collect statistics and write the gathered data into an output file.
We allow choosing between different tool interfaces, execution backends and output formats.

## Getting started

After downloading the repository, you can install this project as a package using pip:
```
pip install -e <path/to/benchmax-py>
```
The `-e` (for "editable") allows you to edit/update this repository without needing to reinstall benchmax.

This installs the executable(s) found in `benchmax-py/bin`, which lets you call the command `benchmax` from anywhere (a more detailed explanation for the command follows below). Note that the directory to which the scripts are installed might need to be added to your `PATH`.

This will also allow you to import the sources of this project, if you want to call the functions from python or, more importantly, if you want to use the included utilities for inspecting the benchmarking results.
```python
import benchmax.inspection as ev
```

## Benchmarking

The general idea of benchmax is that you have a list of tools, each of which you want to evaluate on all test cases (benchmarks) within one or more given directories.

That is, for each tool-test-pair, benchmax executes the tool on the test case and gathers statistics like the result, runtime and memory consumption, but it can also collect custom statistics from the output, if an appropriate parser for the given tool is provided (See Section Tools below).

A usual call to benchmax looks something like this:
```
benchmax -T 1m -M 2G -b local -S smtrat-static -D QF_NRA -C output.csv
```
This would use the local backend (more on backends later) to benchmark the `smtrat-static` tool on all instances contained in the `QF_NRA`folder with a timeout of 1 minute and memory limit of 2 GB per instance, and the results would be written to `output.csv`.

More generally, calls should have this form:

```
benchmax <limit opts> <backend opts> <tool opts> <input opts> <output opts> [other opts] 
```

The following table explains the options in more detail:

| Category | Option | Explanation | Type |
|----------|--------|-------------|----------|
| Limits | `-T/--timeout <time>` | the time limit per instance. The value should be formatted like `[<hours>h][<minutes>m][<seconds>s]`, e.g. 1h or 1m30s| required |
|| `-M/--memout <memory>` | the memory limit per instance. The value should be a positive integer followed by one of the units `K/Ki` (kilobytes), `M/Mi` (Megabytes) or `G/Gi` (Gigabytes), e.g. 2GB. | required |
| Backend | `-b/--backend <backend>` | the backend to use. Currently, the backend can only be `local` or `slurm`. More information on backends below. | required |
| Tools | `--tool/-S/-Z/... <path>` | the tool(s) to evaluate. For generic tools without custom parser, `--tool` can be used. For some tools, benchmax provides custom parsers, e.g. SMT-RAT (`-S`) or z3 (`-Z`). For a complete list, see Section "Tools" | one ore more |
|| `-s/--statistics` | collect additional statistics, if possible. For example, SMT-RAT and z3 can provide such statistics. | optional |
| Input | `-D/--directory <path>` | path to a directory containing the test cases. All files the the given directories **and their subdirectories** will be considered. | one or more, required unless `--fromlist` is used|
| Input | `--fromlist <path>` | path to a file listing the file names of the test cases (one in each line). | one or more, required unless `-D` is used|
| Output | `-C/--output-csv <file.csv>` | name of a CSV file to which the output should be written. **Recommended format.** | required unless `-X` is set |
|  | `-X/--output-xml <file.xml>` | name of an XML file to which the output should be written. | required unless `-C` is set |
|  | `--split-output` | split output into one file for each tool. The output files will be prefixed with the name given for `-C/-X`| optional |
| Other | `-h/--help` | show help message| optional |
|  | `--settings` | show used settings without executing | optional |
|  | `--verbose` | show debug level output | optional |
|  | `--quiet` | show only the most important output | optional |
|  | `--config <configfile>` | load options from the given config file (more information below). | optional, 0 or more|


### Configuration Files
To simplify benchmarking runs with (mostly) the same options, you can use config files containing some or all options.
A config file contains the options just like you would write them in the terminal, but line breaks are also allowed.

Benchmax will first collect the contents of all given config files, append them to the other given program options and then run as usual.
You can combine multiple config files, but be careful to define the same option in multiple files.

### Local Backend

Runs the benchmarks locally and (for now) sequentially.
This can take a lot of time for large benchmark sets.

### Slurm Backend

We provide a backend for running benchmax using a slurm array job.
This requires additional options:
- `--slurm.tmp-dir <directory>` (required): directory for storing temporary result files.
- `--slurm.keep-logs` (optional): keep the temporary result files instead of deleting them at the end.
- `--slurm.archive-logs <archive-name>` (optional): store temporary files in a tgz archive with the given name.
- `--slurm.array-size <size>` (required): maximum size of the job array. If there are fewer tool-file pairs, the array is shrinked to fit.
- `--slurm.sbatch-options=<option-string>` (required): additional options to pass to slurm, in quotes. **Important:** the `=` is needed to prevent that `argparse` interprets these as `benchmax`-options.
- `--slurm.env <file>` (optional): file for loading an environment (needed on the RWTH-Cluster). As a default `load_environment` is assumed.

### Tools

Currently, there are custom output parsers for the following tools:
- `-S/--smtrat`: An SMT solver based on SMT-RAT, with SMT-LIB interface
- `-Q/--smtrat-qe`: A quantifier elimination tool based on SMT-RAT, with SMT-LIB interface
- `-Z/--z3`: the z3 SMT solver, with SMT-LIB interface
- `--z3-qe`: z3 when used for quantifier elimination, with SMT-LIB interface
- `--redlog`: redlog quantifier elimination (handles .red files)
- `--cdd`: polyhedron projection with CDDlib (.ine files)
- `--tool`: any generic tool, without custom output parsing.

To add a new tool, create a new subclass of `benchmax.tools.Tool` and implement `get_command_line`, `can_handle` and `parse_additional` to your needs.

### Running Tools with Options

To pass a tool with specific program options to benchmax, put the tool and options in quotes, e.g. `benchmax -S "smtrat-static --stats.print" <other options...>`

## Analyzing the Results

In its `benchmax.inspection` module, Benchmax provides some utilities for inspecting the resulting CSV or XML files.
Note that most of these utilities are very much tailored to the context of SMT solvers and not really suited for other tools.

As mentioned before, this module can be loaded to a python script or jupyter notebook using e.g.
```python
import benchmax.inspection as bi
```

You can find an [example jupyter notebook](examples/inspection-example.ipynb) illustrating the inspection utilities in the `examples` folder.

## Hints

If you are using VSCode and Pylance cannot resolve the import of (e.g.) `benchmax.inspection`, try adding the path of `benchmax-py` to the `python.analysis.extraPath` option in vscode settings (`settings.json`).
The problem is related to using an editable installation with pip.