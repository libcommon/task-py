# task-py: Python Task Execution Framework

## Overview

One day you need to write a script to process some data, so you sit down and write it. The filepath and other parameters
are hard-coded, but it works. A few days later, you need to do the same thing, but need to accept a filepath on the
command line and maybe one more parameter, so you refactor some functionality into functions and create a simple CLI
using `sys.argv`.  Then a coworker asks if he/she/they could use the script, so you finally break down and use `argparse`
to write a better CLI.  If this cycle sounds familiar, `task-py` can help by allowing you to skip steps one and two, while
writing interoperable, composable tools.

## Installation

### Install from PyPI (preferred method)

```bash
pip install lc_task
```

### Install Directly with Pip and Git

```bash
pip install git+https://github.com/libcommon/task-py.git@vx.x.x#egg=lc_task
```

where `x.x.x` is the version you want to download.

### Install from Cloned Repo

```bash
git clone ssh://git@github.com/libcommon/task-py.git && \
    cd task-py && \
    pip install .
```

## Dependencies

The `tool.poetry.*dependencies` sections in [pyproject.toml](pyproject.toml) contain the app and dev dependencies.
See [DEVELOPMENT.md](DEVELOPMENT.md) for local development and build dependencies.

## Getting Started

### Creating a Task

Creating a `Task` is simple: specify some (optional) attributes and implement `Task._perform_task`, which performs the primary unit of work.
For example, you could implement a task that takes a file path and prints the data of that file to stdout:

```python
import typing
from pathlib import Path

from lc_task import Task, taskclass


@taskclass
class CatFileTask(Task):
    """Print contents of a file to stdout."""
    input_path: typing.Optional[Path] = None

    def _perform_task(self) -> None:
        if self.input_path is None:
            raise ValueError("No input path provided")
        if not self.input_path.is_file():
            raise FileNotFoundError(self.input_path)
        print(self.input_path.read_text())

if __name__ == "__main__":
    import sys
    # Example of how to use CatFileTask.run() to run the task
    CatFileTask(input_path=Path(sys.argv[0])).run()
```

In the example above, we define an attribute `input_path` on `CatFileTask` to store the input file path.
For tasks that require some setup and teardown steps, use the `Task._preamble` and `Task._postamble` functions,
which get called before and after the primary unit of work is completed.
To run this task explicitly, use the `CatFileTask.run` method.

### Accepting Command Line Input

To create a task that takes command line input (using `argparse`), create a child class of `CliTask` that defines
the name of the command, a brief description, and the command line arguments (plus optional command aliases). Taking the example above:

```python
import typing
from pathlib import Path

from lc_task import CliTask, Task, taskclass


@taskclass
class CatFileTask(Task):
    """Print contents of a file to stdout."""
    input_path: typing.Optional[Path] = None

    def _perform_task(self) -> None:
        if self.input_path is None:
            raise ValueError("No input path provided")
        if not self.input_path.is_file():
            raise FileNotFoundError(self.input_path)
        print(self.input_path.read_text())


@taskclass
class CatFileCliTask(CliTask):
    _task_cls = CatFileTask
    command = "cat"
    aliases = ["c"]
    description = "Print contents of a file to stdout."

    @classmethod
    def gen_command_parser(cls, parser: typing.Optional[ArgumentParser] = None) -> ArgumentParser:
        parser = super(CatFileCliTask, cls).gen_command_parser()
        parser.add_argument("input_path", type=Path, help="Path to input file")
        return parser


if __name__ == "__main__":
    CatFileTask.run_command()
```

This example shows a few key features of the library:

1. The command line parser for a CLI task is defined using the `CliTask.gen_command_parser` function.
2. Command aliases can be added using the `CliTask.aiases` attribute.
3. `Task`s and `CLiTask`s are easily composable using the `_task_cls` attribute of `CliTask`.
By default, `CliTask` merges the command line arguments with an instance of `_task_cls` and runs the task.
This behavior can be customized by overriding `Clitask._gen_task` and `Clitask._perform_task`.

For defining more complex, hierarchical command line interfaces with subcommands, look at the documentation for `cli.gen_cli_parser`.
It allows you to define your command line app with a mapping of commands to actions, then generates the CLI for you.

### Pipelines and Message Passing

Anyone who has used Bash, PowerShell, or other scripting languages is familiar with the idea of composability and pipes:
writing simple commands that return structured data recognized by other commands can be very powerful.
Python does not support this style of programming out of the box, but it does support overloading operators for custom types,such as the bitwise or operator (`|`).
In Python, the [`__ror__` builtin method](https://docs.python.org/3/reference/datamodel.html#object.__or__)
is called when using the bitwise or operator on two objects where the first (left side) doesn't implement `__or__`.

`task-py` takes advantage of this flexibility to allow piping `Task`s together to create pipelines. For example, suppose
you were writing a CSV handing toolkit and wanted to create a command line app that reads data from a CSV and removes some columns.
There are two clear steps in this pipeline:

1. Read data from the CSV into some data structure
2. Remove specified columns (and write to stdout)

```python
import csv
import typing
from pathlib import Path

from lc_task import CliTask, Task, TaskResult, taskclass


@taskclass
class CsvColumnRemovalTask(Task):
    """Remove specified columns from frows in a CSV."""
    __slots__ = ("columns", "input_file", "reader")
    columns_to_remove: typing.Optional[typing.List[str]] = None
    records: typing.Optional[typing.List[typing.Dict[str, typing.Any]]] = None

    def _perform_task(self) -> None:
        if self.columns and self.records:
            # Print the header row
            print(",".join(records[0].keys()))
            for record in records:
                for column in self.columns:
                    del record[column]
                # Print the record
                print(", ".join(record.values()))


@taskclass
class CsvReaderTaskResult(TaskResult):
    records: typing.Optional[typing.List[typing.Dict[str, typing.Any]]] = None


@taskclass
class CsvReaderTask(Task):
    """Read data from a CSV into a `csv.DictReader` object."""
    _result_cls = CsvReaderTaskResult

    input_path: typing.Optional[Path] = None

    def _perform_task(self) -> None:
        if self.input_path is None:
            raise ValueError("Must provide path to or file handle of CSV file")
        if not self.input_path.is_file():
            raise FileNotFoundError(self.input_file)

        with self.input_path.open(newline="") as input_file:
            self.result.records = [record for record in csv.DictReader(input_file, csv.unix_dialect)]


@taskclass
class RemoveColumnsCliTask(CliTask):
    command = "remove-columns"
    description = "Remove columns from a CSV and write to disk."

    @classmethod
    def gen_command_parser(cls, parser: Optional[ArgumentParser] = None) -> ArgumentParser:
        parser = super(RemoveColumnsCliTask, cls).gen_command_parser()
        parser.add_argument("input_path", type=Path, help="Path to input file")
        parser.add_argument("columns", nargs=+, help="Column names to remove")
        return parser

    def _perform_task(self) -> None:
        columns_to_remove: typing.List[str] = self.args.columns
        input_path: Path = self.args.path = self.args.input_path
        # Pipe the output of CSVReaderTask to CSVColumnRemovalTask
        (CSVReaderTask(input_path=input_path).run() |
         CSVColumnRemovalTask(columns_to_remove=columns_to_remove))


if __name__ == "__main__":
    RemoveColumnsCLITask.run_command()
```

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for development instructions.

## Contributing/Suggestions

Contributions and suggestions are welcome! To make a feature request, report a bug, or otherwise comment on existing functionality, please file an issue.
For contributions please submit a PR, but make sure to lint, type-check, and test your code before doing so. Thanks in advance!
