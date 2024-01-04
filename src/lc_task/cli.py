# mypy: disable-error-code="call-arg"
from __future__ import annotations

import logging
import sys
import typing
from argparse import ArgumentParser, Namespace

from .task import Task, TaskResult, taskclass

__author__ = "libcommon"
logger = logging.getLogger(__name__)
#: Command line parser generator config type (see :func:`.gen_cli_parser`).
CliParserConfig = typing.Dict[
    typing.Union[typing.Type[Task], typing.Tuple[typing.Union[str, typing.Tuple[str, ...]], str]],
    typing.Optional["CliParserConfig"],
]


@taskclass
class CliTask(Task):
    """Base task for tasks instantiated via command line.

    Integrates with :class:`ArgumentParser` for defining command line parsers.

    Examples:

    Create a CLI task to count the number of lines in a file:

    >>> import tempfile
    >>> from argparse import ArgumentParser
    >>> from pathlib import Path
    >>> from lc_task import TaskResult, taskclass
    >>> from lc_task.cli import CliTask
    >>> @taskclass
    ... class CountLinesTask(Task):
    ...     input_path: typing.Optional[Path] = None
    ...     def _perform_task(self) -> None:
    ...         if self.input_path is None or not self.input_path.is_file():
    ...             raise FileNotFoundError(self.input_path)
    ...         num_lines = 0
    ...         with self.input_path.open() as input_file:
    ...             for _ in input_file:
    ...                 num_lines += 1
    ...         print(num_lines)
    ...
    >>> @taskclass
    ... class CountLinesCliTask(CliTask):
    ...     _task_cls = CountLinesTask
    ...     command = "linecount"
    ...     description = "Count the number of lines in a file"
    ...     @classmethod
    ...     def gen_command_parser(cls, parser: typing.Optional[ArgumentParser] = None) -> ArgumentParser:
    ...         parser = super(CountLinesCliTask, cls).gen_command_parser(parser)
    ...         parser.add_argument("input_path", type=Path, help="Path to input file")
    ...         return parser
    ...
    >>> with tempfile.NamedTemporaryFile() as tmp_file:
    ...     # Write ten lines to file
    ...     for _ in range(10):
    ...         __ = tmp_file.write(b"\\n")
    ...     # Flush writes
    ...     tmp_file.flush()
    ...     _ = CountLinesCliTask.run_command(argv=[tmp_file.name])
    10
    """

    #: Task class to run (see :meth:`.CliTask._gen_task`).
    _task_cls: typing.ClassVar[typing.Optional[typing.Type[Task]]] = None
    #: Aliases of the CLI command for this task
    aliases: typing.ClassVar[typing.Optional[typing.List[str]]] = None
    #: Name of the CLI command
    command: typing.ClassVar[str] = ""
    #: Description of CLI command
    description: typing.ClassVar[str] = ""

    #: Command line arguments
    args: typing.Optional[Namespace] = None

    @classmethod
    def __run_command(cls, args: Namespace) -> TaskResult:
        """Run task from command line arguments."""
        if hasattr(args, "func"):
            del args.func
        return cls(args=args).run()

    @classmethod
    def gen_command_parser(cls, parser: typing.Optional[ArgumentParser] = None) -> ArgumentParser:
        """Generate command line parser.

        Args:
            parser: parser to add arguments to.

        Returns:
            Updated command line parser.

        Raises:
            ValueError: if class variables :attr:`.CliTask.command` and :attr:`.CliTask.description` are not set.
        """
        if not (cls.command and cls.description):
            raise ValueError("command and description class variables must be defined")
        if parser is None:
            parser = ArgumentParser(prog=cls.command, description=cls.description)
        parser.set_defaults(func=cls.__run_command)
        return parser

    @classmethod
    def run_command(
        cls,
        argv: typing.Optional[typing.List[str]] = None,
        known_args: bool = False,
    ) -> TaskResult:
        """Parse command line arguments and run task.

        Args:
            argv: command line arguments to parse.
            known_args: only parse known args (see :meth:`ArgumentParser.parse_known_args`).
        """
        if argv is None:
            argv = sys.argv
        parser = cls.gen_command_parser()
        if known_args:
            args, _ = parser.parse_known_args(argv)
        else:
            args = parser.parse_args(argv)
        return args.func(args)  # type: ignore

    def _gen_task(self) -> typing.Optional[Task]:
        """Generate new task.

        Default implementation merges :attr:`.CliTask.args` with instance of
        :attr:`.CliTask._task_cls` if it's not ``None``.
        """
        if self._task_cls is not None:
            return self._task_cls().merge_object(self.args)
        return None

    def _perform_task(self) -> None:
        task = self._gen_task()
        if task is not None:
            task.run()


def gen_cli_parser(root_parser: ArgumentParser, parser_config: CliParserConfig) -> ArgumentParser:
    """Generate commmand line parser from configuration.

    The configuration is a dict that maps subcommands to :class:`.CliTask` classes.
    Uses the configuration to generate a subcommand-style CLI like ``git`` (e.g. ``git clone``, ``git pull``, etc).

    Args:
        root_parser: root parser to which all other parsers will be attached.
        parser_config: mapping of subcommands to :class:`.CliTask` defining the CLI hierarchy.

    Returns:
        ``root_parser`` with the subcommands defined in ``parser_config``.

    Raises:
        TypeError: if subcommand isn't of type :data:`.CliParserConfig`.

    Examples:

    Given the parser config:

    .. code-block:: python

        {
            ("amphibians", "Amphibian animals"): {
                FrogsTask: {},
            },
            (("invertebrates", "i"), "Invertebrate animals"): {
                WormsTask: {},
                ArthropodsTask: {},
            },
            ("reptiles", "Reptile animals"): {
                SnakesTask: {},
            },
            (("vertebrates", "v"), "Vertebrate animals"): {
                FishTask: {},
                BirdsTask: {},
            },
        }

    The following command line paths would be valid (assuming ``animals.py`` is the root Python file):
        * ``animals.py amphibians``
        * ``animals.py amphibians frogs``
        * ``animals.py invertebrates``
        * ``animals.py i``
        * ``animals.py invertebrates worms``
        * ``animals.py i worms``
        * ``animals.py invertebrates arthropods``
        * ``animals.py i arthropods``
        * ``animals.py reptiles``
        * ``animals.py reptiles snakes``
        * ``animals.py vertebrates``
        * ``animals.py v``
        * ``animals.py vertebrates fish``
        * ``animals.py v fish``
        * ``animals.py vertebrates birds``
        * ``animals.py v birds``
    """
    if parser_config:
        # Store subcommand on ``args`` as ``subcommand``
        subparsers = root_parser.add_subparsers(dest="subcommand")
        for subcommand, subparser_config in parser_config.items():
            if isinstance(subcommand, tuple):
                # ("command", "description")
                if isinstance(subcommand[0], str):
                    command, description = subcommand
                    aliases: typing.Tuple[str, ...] = ()
                # (("command1", "command2", ..., "commandN"), "description")
                else:
                    command_and_aliases, description = subcommand
                    command = command_and_aliases[0]
                    aliases = command_and_aliases[1:]  # type: ignore
                subcommand_parser = subparsers.add_parser(command, aliases=aliases, help=description)  # type: ignore
            # NOTE: Potentially raise exception here if root_parser runs another CliTask,
            # as the parent of a CliTask should _not_ be another CliTask.
            elif issubclass(subcommand, CliTask):
                # Add subcommand parser and configuration from task
                subcommand_parser = subcommand.gen_command_parser(
                    subparsers.add_parser(
                        subcommand.command,
                        aliases=(subcommand.aliases or []),
                        help=subcommand.description,
                    )
                )
            if subparser_config:
                gen_cli_parser(subcommand_parser, subparser_config)
    return root_parser
