# Benchmax: an automated benchmarking utility

This is work in progress. Contact Valentin (promies at cs dot rwth-aachen.de).

## Getting started

You can install this project as a package using pip:
```
pip install -e <path/to/benchmax-py>
```

This will allow you to import the sources of this project like e.g.
```python
import benchmax.inspection as ev
```
It also installs the executable(s) found in `benchmax-py/bin`, which lets you call the command `benchmax` from anywhere. Note that the directory to which the scripts are installed might need to be added to your `PATH`.

The `-e` (for ``editable'') allows you to edit/update this repository without needing to reinstall benchmax.