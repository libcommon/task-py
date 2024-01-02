import logging
import sys
import typing
from argparse import ArgumentParser, Namespace

from .task import Task, TaskResult

__author__ = "libcommon"
logger = logging.getLogger(__name__)
CLIParserConfig = typing.Dict[typing.Union[typing.Type[Task], typing.Tuple[str, str]], typing.Optional[typing.Any]]


class CLITask(Task):  # pylint: disable=abstract-method
    """Base class for tasks that can be instantiated via command line
    using argparse.ArgumentParser.
    """

    __slots__ = ()

    # TODO: change these to lowercase in next breaking version
    COMMAND: typing.ClassVar[typing.Optional[str]] = None  # pylint: disable=invalid-name
    DESCRIPTION: typing.ClassVar[typing.Optional[str]] = None  # pylint: disable=invalid-name

    @classmethod
    def __run_command(cls, args: Namespace) -> typing.Optional[TaskResult]:
        """
        Args:
            args    => parsed command line arguments
        Returns:
            Result of running task from command line arguments.
        Preconditions:
            N/A
        Raises:
            N/A
        """
        if hasattr(args, "func"):
            del args.func
        return cls().merge_object(args).run()

    @classmethod
    def gen_command_parser(cls, parser: typing.Optional[ArgumentParser] = None) -> ArgumentParser:
        """
        Args:
            parser  => argument parser to add arguments to (default: None)
        Returns:
            Configured command line parser.
        Preconditions:
            N/A
        Raises:
            ValueError: if class variables COMMAND and DESCRIPTION are not set
        """
        if not (bool(cls.COMMAND) and bool(cls.DESCRIPTION)):
            raise ValueError("COMMAND and DESCRIPTION class variables must be defined")
        if parser is None:
            parser = ArgumentParser(prog=cls.COMMAND, description=cls.DESCRIPTION)
        parser.set_defaults(func=cls.__run_command)
        return parser

    @classmethod
    def run_command(
        cls, argv: typing.List[str] = sys.argv, known_args: bool = False
    ) -> typing.Optional[TaskResult]:  # pylint: disable=dangerous-default-value
        """
        Args:
            argv        => command line args
            known_args  => only parse known args
        Procedure:
            Parse command line args and run task.
        Preconditions:
            N/A
        Raises:
            N/A
        """
        parser = cls.gen_command_parser()
        if known_args:
            args, _ = parser.parse_known_args(argv)
        else:
            args = parser.parse_args(argv)
        return args.func(args)  # type: ignore


def gen_cli_parser(root_parser: ArgumentParser, parser_config: CLIParserConfig) -> ArgumentParser:
    """
    Args:
        root_parser     => root parser to which all other parsers will be attached
        parser_config   => tree of CLITasks defining CLI hierarchy
    Returns:
        Generated command line parser with subcommands defined in parser_config.
        For example, given the parser config:
            {
                ("invertebrates", "Invertebrate animals"): {
                    WormsTask: {},
                    ArthropodsTask: {},
                },
                ("vertebrates", "Vertebrate animals"): {
                    FishTask: {},
                    BirdsTask: {},
                },
            }
        The following command line paths would be valid (assuming animals.py is the root Python file):
            1) animals.py invertebrates
            2) animals.py invertebrates worms
            3) animals.py invertebrates arthropods
            4) animals.py vertebrates
            5) animals.py vertebrates fish
            6) animals.py vertebrates birds
    Preconditions:
        N/A
    Raises:
        typing.TypeError: if subcommand doesn't conform to type CLIParserConfig
    """
    # If parser config isn't empty dictionary
    if bool(parser_config):
        # Add subparsers to parent parser
        subparsers = root_parser.add_subparsers(dest="subcommand")
        # For each item defined in current level of parser config
        for subcommand, subparser_config in parser_config.items():
            # If subcommand is tuple
            if isinstance(subcommand, tuple):
                # Desctructure to get command and description
                command, description = subcommand
                # Add subcommand parser
                subcommand_parser = subparsers.add_parser(command, help=description)
            # If subcommand is CLITask
            # NOTE: Potentially raise exception here if root_parser runs another CLITask,
            # as the parent of a CLITask should _not_ be another CLITask.
            elif issubclass(subcommand, CLITask):
                # Add subcommand parser
                subcommand_parser = subparsers.add_parser(
                    subcommand.COMMAND, help=(subcommand.DESCRIPTION or "")  # type: ignore
                )
                # Add configuration for subcommand
                subcommand_parser = subcommand.gen_command_parser(subcommand_parser)
            else:
                raise TypeError(f"invalid subcommand type {type(subcommand)}")
            # If subparser_config defined, generate subcommand parsers
            if bool(subparser_config):
                gen_cli_parser(subcommand_parser, subparser_config)  # type: ignore
    return root_parser
