import typing
import unittest
import unittest.mock as mock
from argparse import ArgumentParser, Namespace

from lc_task.cli import CLITask, gen_cli_parser


class WormsTask(CLITask):
    __slots__ = ()

    COMMAND = "worms"
    DESCRIPTION = "Worms task"

    @classmethod
    def gen_command_parser(cls, parser: typing.Optional[ArgumentParser] = None) -> ArgumentParser:
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
    __slots__ = ()

    COMMAND = "fish"
    DESCRIPTION = "Fish task"

    @classmethod
    def gen_command_parser(cls, parser: typing.Optional[ArgumentParser] = None) -> ArgumentParser:
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

    def test_gen_cli_parser(self):
        root_parser = ArgumentParser(add_help=False)
        root_parser.add_argument(
            "--level",
            type=str,
            required=False,
            default="INFO",
            help="Logging level (default: INFO)",
            dest="log_level",
        )

        def print_help(_: Namespace) -> None:
            root_parser.print_help()

        root_parser.set_defaults(func=print_help)

        tests = [
            ("Root parser only", dict(), ["--level", "DEBUG"], Namespace(log_level="DEBUG", func=print_help)),
            (
                "Single subcommand - depth of 1",
                {WormsTask: dict()},
                ["worms", "Lumbricus", "terrestris"],
                Namespace(
                    log_level="INFO",
                    genus="Lumbricus",
                    species="terrestris",
                    subcommand="worms",
                    func=WormsTask._CLITask__run_command,
                ),
            ),  # pylint: disable=no-member
            (
                "Two subcommands, depth of 1",
                {WormsTask: dict(), ArthropodsTask: dict()},
                ["--level", "WARNING", "arthropods", "Palaemonias", "ganteri"],
                Namespace(
                    log_level="WARNING",
                    genus="Palaemonias",
                    species="ganteri",
                    subcommand="arthropods",
                    func=ArthropodsTask._CLITask__run_command,
                ),
            ),  # pylint: disable=no-member
            (
                "Three subcommands, with tuples, depth of 2",
                {("invertebrates", "Invertebrate animals"): {WormsTask: dict(), ArthropodsTask: dict()}},
                ["invertebrates", "arthropods", "Neotibicen", "linnei"],
                Namespace(
                    log_level="INFO",
                    genus="Neotibicen",
                    species="linnei",
                    subcommand="arthropods",
                    func=ArthropodsTask._CLITask__run_command,
                ),
            ),  # pylint: disable=no-member
            (
                "Five subcommands, with tuples, depth of 2",
                {
                    ("invertebrates", "Invertebrate animals"): {
                        WormsTask: dict(),
                        ArthropodsTask: dict(),
                    },
                    ("vertebrates", "Vertebrate animals"): {
                        FishTask: dict(),
                    },
                },
                ["vertebrates", "fish", "Canada", "--fresh-water"],
                Namespace(
                    log_level="INFO",
                    region="Canada",
                    fresh_water=True,
                    subcommand="fish",
                    func=FishTask._CLITask__run_command,
                ),
            ),  # pylint: disable=no-member
        ]

        with mock.patch.object(ArgumentParser, "exit"):
            for test_name, parser_config, argv, expected in tests:
                with self.subTest(test_name=test_name):
                    parser = ArgumentParser(prog="animals.py", description="CLI for animals", parents=[root_parser])
                    parser = gen_cli_parser(parser, parser_config)
                    args = parser.parse_args(args=argv)
                    self.assertEqual(expected, args)
