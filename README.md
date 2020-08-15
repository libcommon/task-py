# `task-py`

## Overview

One day you need to write a script to process some data, so you sit down and write it. The filepath and other parameters
are hard-coded, but it works. A few days later, you need to do the same thing, but need to accept a filepath on the
command line and maybe one more parameter, so you refactor some functionality into functions and create a simple CLI
using `sys.argv`.  Then a coworker asks if he/she/they could use the script, so you finally break down and use `argparse`
to write a better CLI.  If this cycle sounds familiar, `task-py` can help by allowing you to skip steps one and two, while
writing interoperable, composable tools.

## Installation

### Install from PyPi (preferred method)

```bash
pip install lc-task
```

### Install from GitHub with Pip

```bash
pip install git+https://github.com/libcommon/task-py.git@vx.x.x#egg=lc_task
```

where `x.x.x` is the version you want to download.

## Install by Manual Download

To download the source distribution and/or wheel files, navigate to
`https://github.com/libcommon/task-py/tree/releases/vx.x.x/dist`, where `x.x.x` is the version you want to install,
and download either via the UI or with a tool like wget. Then to install run:

```bash
pip install <downloaded file>
```

Do _not_ change the name of the file after downloading, as Pip requires a specific naming convention for installation files.

## Dependencies

`task-py` does not have external dependencies. Only Python versions >= 3.6 are officially supported.

## Getting Started

### Creating a Task

Creating a `Task` is simple: specify some (optional) attributes and implement `Task._perform_task`, which performs the primary
unit of work. For example, you could implement a task that takes a file path and prints the data of that
file to stdout:

```python
from pathlib import Path

from lc_task import Task


class CatFileTask(Task):
    """Print contents of a file to stdout."""
    __slots__ = ("_input_path",)

    def __init__(self, input_path: Path, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._input_path

    def _perform_task(self) -> None:
        if not self._input_path.is_file():
            raise FileNotFoundError(str(self._input_path))
        with self._input_path.open() as input_file:
            print(input_file.read())
```

In the example above, we defined an attribute `_input_path` on `CatFileTask` to store the input file path. However, you
can also use the `state` dict attribute to store arbitrary state. For tasks that require some setup and teardown steps,
use the `Task._preamble` and `Task._postamble` functions, which get called before and after the primary unit of work is completed.
To run this task explicitly, you would use the `Task.run` method.

### Accepting Command Line Input

To create a single task that takes command line input (using `argparse`), create a child class of `CLITask` that defines the
name of the command, a brief description, and the command line arguments. Taking the example above:

```python
from pathlib import Path

from lc_task import CLITask


class CatFileTask(CLITask):
    __slots__ = ("_input_path",)

    COMMAND = "cat"
    DESCRIPTION = "Print contents of a file to stdout."

    @classmethod
    def gen_command_parser(cls, parser: Optional[ArgumentParser] = None) -> ArgumentParser:
        parser = super().gen_command_parser()
        parser.add_argument("_input_path", type=Path, metavar="INPUT_PATH", help="Path to input file")
        return parser

    def _perform_task(self) -> None:
        if not self._input_path.is_file():
            raise FileNotFoundError(str(self._input_path))
        with self._input_path.open() as input_file:
            print(input_file.read())


if __name__ == "__main__":
    CatFileTask.run_command()
```

For defining more complex, hierarchical command line interfaces with subcommands, take a look at the docstring
for `cli.gen_cli_parser`. It allows you to define your command line app with a mapping of commands to actions,
then generates the CLI for you.

### Pipelines and Message Passing

Anyone who has used Bash, PowerShell, or other scripting languages is familiar with the idea of composability and pipes:
writing simple commands that return structured data recognized by other commands can be very powerful.  Python does not
support this style of programming out of the box, but it does support overloading operators for custom types, such as the
bitwise or operator (`|`).  In Python, the [`__ror__` builtin method](https://docs.python.org/3/reference/datamodel.html#emulating-numeric-types)
is called when using the bitwise or operator on two objects where the first (left side) doesn't implement `__or__`.

`task-py` takes advantage of this flexibility to allow piping `Task`s together to create pipelines. For example, suppose
you were writing a CSV handing toolkit and wanted to createa a command line app that reads data from a CSV and removes
some columns.  There are two clear steps in this pipeline:

1. Read data from the CSV into some data structure
2. Remove specified columns (and write to stdout)

```python
import csv
from pathlib import Path
from typing import List, Optional, TextIO

from lc_task import CLITask, Task, TaskResult


class CSVColumnRemovalTask(Task):
    """Remove specified columns from frows in a CSV."""
    __slots__ = ("columns", "input_file", "reader")

    def __init__(self, *args, columns: Optional[List[str]] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.columns = columns

    def _perform_task(self) -> None:
        for record in reader:
            for column in self.columns:
                del record[column]
            print(", ".join(record))

    def _preamble(self) -> None:
        self.input_file.close()


class CSVReaderTaskResult(TaskResult):
    __slots__ = ("input_file", "reader")

    def __init__(self: input_file: Optional[TextIO] = None, reader: Optional[csv.DictReader] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.input_file = input_file
        self.reader = reader


class CSVReaderTask(Task):
    """Read data from a CSV into a `csv.DictReader` object."""
    __slots__ = ("input_path",)

    @staticmethod
    def gen_task_result() -> TaskResult:
        return CSVReaderTaskResult()

    def __init__(self, *args, input_path: Optional[Path] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.input_path = input_path

    def _perform_task(self) -> None:
        # Need to check self.input_path because it could be provided in
        # __init__ or via merge_object
        if not self.input_path:
            raise ValueError("must provide path to CSV file")

        input_file = self.input_path.open(newline="")
        reader = csv.DictReader(input_file, dialect=csv.unix_dialect)
        # Using a defined TaskResult type here, but could also just use a dict
        self.result = CSVReaderTaskResult(input_file = input_file, reader = reader)


class RemoveColumnsCLITask(CLITask):
    __slots__ = ("columns", "input_path")

    COMMAND = "remove-columns"
    DESCRIPTION = "Remove columns from a CSV and write to disk."

    @classmethod
    def gen_command_parser(cls, parser: Optional[ArgumentParser] = None) -> ArgumentParser:
        parser = super().gen_command_parser()
        parser.add_argument("input_path", type=Path, help="Path to input file")
        parser.add_argument("columns", nargs=+, help="Column names to remove")
        return parser

    def _perform_task(self) -> None:
        # Pipe the output of CSVReaderTask to CSVColumnRemovalTask
        (CSVReaderTask(input_path = self.input_path).run() |
         CSVColumnRemovalTask(columns = self.columns))


if __name__ == "__main__":
    RemoveColumnsCLITask.run_command()
```

## Contributing/Suggestions

Contributions and suggestions are welcome! To make a feature request, report a bug, or otherwise comment on existing
functionality, please file an issue. For contributions please submit a PR, but make sure to lint, type-check, and test
your code before doing so. Thanks in advance!
