## -*- coding: UTF-8 -*-
## cli.py
##
## Copyright (c) 2019 libcommon
##
## Permission is hereby granted, free of charge, to any person obtaining a copy
## of this software and associated documentation files (the "Software"), to deal
## in the Software without restriction, including without limitation the rights
## to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
## copies of the Software, and to permit persons to whom the Software is
## furnished to do so, subject to the following conditions:
##
## The above copyright notice and this permission notice shall be included in all
## copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
## OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
## SOFTWARE.


from argparse import ArgumentParser, Namespace
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from .task import Task, TaskResult


__author__ = "libcommon"
logger = logging.getLogger(__name__)    # pylint: disable=C0103
CLIParserConfig = Dict[Union[Type[Task], Tuple[str, str]], Optional[Any]]


class CLITask(Task):    # pylint: disable=abstract-method
    """Base class for tasks that can be instantiated via command line
    using argparse.ArgumentParser.
    """
    __slots__ = ()

    COMMAND: Optional[str] = None
    DESCRIPTION: Optional[str] = None

    @classmethod
    def __run_command(cls, args: Namespace) -> Optional[TaskResult]:
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
    def gen_command_parser(cls, parser: Optional[ArgumentParser] = None) -> ArgumentParser:
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
    def run_command(cls, argv: List[str] = sys.argv, known_args: bool = False) -> Optional[TaskResult]:    # pylint: disable=dangerous-default-value
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
        return args.func(args)


def gen_cli_parser(root_parser: ArgumentParser,
                   parser_config: CLIParserConfig) -> ArgumentParser:
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
        TypeError: if subcommand doesn't conform to type CLIParserConfig
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
                subcommand_parser = subparsers.add_parser(subcommand.COMMAND,                  # type: ignore
                                                          help=(subcommand.DESCRIPTION or ""))
                # Add configuration for subcommand
                subcommand_parser = subcommand.gen_command_parser(subcommand_parser)
            else:
                raise TypeError("invalid subcommand type {}".format(type(subcommand)))
            # If subparser_config defined, generate subcommand parsers
            if bool(subparser_config):
                gen_cli_parser(subcommand_parser, subparser_config) # type: ignore
    return root_parser


if os.environ.get("ENVIRONMENT") == "TEST":
    import unittest
    import unittest.mock as mock


    class WormsTask(CLITask):
        __slots__ = ()

        COMMAND = "worms"
        DESCRIPTION = "Worms task"

        @classmethod
        def gen_command_parser(cls, parser: Optional[ArgumentParser] = None) -> ArgumentParser:
            parser = super().gen_command_parser(parser)
            parser.add_argument("genus")
            parser.add_argument("species")
            return parser

        def _perform_task(self) -> None:
            print("Worms!")


    class ArthropodsTask(WormsTask):
        __slots__ = ()

        COMMAND = "arthropods"
        DESCRIPTION = "Arthropods task"

        def _perform_task(self) -> None:
            print("Arthropods!")


    class FishTask(CLITask):
        __slots__ = ("region",)

        COMMAND = "fish"
        DESCRIPTION = "Fish task"

        @classmethod
        def gen_command_parser(cls, parser: Optional[ArgumentParser] = None) -> ArgumentParser:
            parser = super().gen_command_parser(parser)
            parser.add_argument("region")
            parser.add_argument("--fresh-water", action="store_true", dest="fresh_water")
            return parser

        def _perform_task(self) -> None:
            print("Fish!")


    class TestCLITask(unittest.TestCase):
        """Test for CLITask and gen_cli_parser"""
        def test_clitask_gen_command_parser_without_parent(self):
            parser = WormsTask.gen_command_parser()
            self.assertEqual(parser.prog, WormsTask.COMMAND)
            self.assertEqual(parser.description, WormsTask.DESCRIPTION)

        def test_clitask_gen_command_parser_with_parent(self):
            parser = WormsTask.gen_command_parser()
            parser = ArthropodsTask.gen_command_parser(parser)
            self.assertEqual(parser.prog, WormsTask.COMMAND)
            self.assertEqual(parser.description, WormsTask.DESCRIPTION)

        def test_clitask_run_command_all_args(self):
            with mock.patch.object(CLITask, "run", lambda self: self.state):
                argv = ["Lumbricus", "terrestris"]
                task_state = WormsTask.run_command(argv=argv)
                self.assertEqual("Lumbricus", task_state.get("genus"))
                self.assertEqual("terrestris", task_state.get("species"))

        def test_clitask_run_command_known_args(self):
            with mock.patch.object(CLITask, "run", lambda self: self.state):
                argv = ["Lumbricus", "terrestris", "--found-on", "land"]
                task_state = WormsTask.run_command(argv=argv, known_args=True)
                self.assertEqual("Lumbricus", task_state.get("genus"))
                self.assertEqual("terrestris", task_state.get("species"))

        def test_clitask_run_command_attribute_arg(self):
            # NOTE: Patched CLITask.run to return the task itself
            with mock.patch.object(CLITask, "run", lambda self: self):
                argv = ["Sagarmatha", "--fresh-water"]
                task = FishTask.run_command(argv=argv)
                self.assertEqual("Sagarmatha", task.region)
                self.assertEqual(True, task.state.get("fresh_water"))

        def test_gen_cli_parser(self):
            root_parser = ArgumentParser(add_help=False)
            root_parser.add_argument("--level",
                                     type=str,
                                     required=False,
                                     default="INFO",
                                     help="Logging level (default: INFO)",
                                     dest="log_level")
            def print_help(_: Namespace) -> None:
                root_parser.print_help()
            root_parser.set_defaults(func=print_help)

            tests = [
                ("Root parser only",
                 dict(),
                 ["--level", "DEBUG"],
                 Namespace(log_level="DEBUG", func=print_help)),
                ("Single subcommand - depth of 1",
                 {WormsTask: dict()},
                 ["worms", "Lumbricus", "terrestris"],
                 Namespace(log_level="INFO",
                           genus="Lumbricus",
                           species="terrestris",
                           subcommand="worms",
                           func=WormsTask._CLITask__run_command)),  # pylint: disable=no-member
                ("Two subcommands, depth of 1",
                 {WormsTask: dict(), ArthropodsTask: dict()},
                 ["--level", "WARNING", "arthropods", "Palaemonias", "ganteri"],
                 Namespace(log_level="WARNING",
                           genus="Palaemonias",
                           species="ganteri",
                           subcommand="arthropods",
                           func=ArthropodsTask._CLITask__run_command)), # pylint: disable=no-member
                ("Three subcommands, with tuples, depth of 2",
                 {("invertebrates", "Invertebrate animals"): {WormsTask: dict(), ArthropodsTask: dict()}},
                 ["invertebrates", "arthropods", "Neotibicen", "linnei"],
                 Namespace(log_level="INFO",
                           genus="Neotibicen",
                           species="linnei",
                           subcommand="arthropods",
                           func=ArthropodsTask._CLITask__run_command)), # pylint: disable=no-member
                ("Five subcommands, with tuples, depth of 2",
                 {
                     ("invertebrates", "Invertebrate animals"): {
                         WormsTask: dict(),
                         ArthropodsTask: dict(),
                     },
                     ("vertebrates", "Vertebrate animals"): {
                         FishTask: dict(),
                     }
                 },
                 ["vertebrates", "fish", "Canada", "--fresh-water"],
                 Namespace(log_level="INFO",
                           region="Canada",
                           fresh_water=True,
                           subcommand="fish",
                           func=FishTask._CLITask__run_command)),   # pylint: disable=no-member
            ]

            with mock.patch.object(ArgumentParser, "exit"):
                for test_name, parser_config, argv, expected in tests:
                    with self.subTest(test_name=test_name):
                        parser = ArgumentParser(prog="animals.py", description="CLI for animals", parents=[root_parser])
                        parser = gen_cli_parser(parser, parser_config)
                        args = parser.parse_args(args=argv)
                        self.assertEqual(expected, args)
