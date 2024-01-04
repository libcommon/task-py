# mypy: disable-error-code="call-arg"
# pylint: disable=invalid-name,missing-class-docstring,missing-function-docstring
import typing
import unittest
from argparse import ArgumentParser, Namespace
from unittest import mock

from lc_task import taskclass
from lc_task.cli import CliParserConfig, CliTask, gen_cli_parser


@taskclass
class WormsTask(CliTask):
    aliases = ["w"]
    command = "worms"
    description = "Worms task."

    @classmethod
    def gen_command_parser(cls, parser: typing.Optional[ArgumentParser] = None) -> ArgumentParser:
        parser = super(WormsTask, cls).gen_command_parser(parser)
        parser.add_argument("genus")
        parser.add_argument("species")
        return parser

    def _perform_task(self) -> None:
        assert self.args is not None
        print(f"Worms! Genus: {self.args.genus}, Species: {self.args.species}")


@taskclass
class ArthropodsTask(WormsTask):
    aliases = []
    command = "arthropods"
    description = "Arthropods task."

    def _perform_task(self) -> None:
        print("Arthropods!")


@taskclass
class FishTask(CliTask):
    aliases = ["f"]
    command = "fish"
    description = "Fish task."

    @classmethod
    def gen_command_parser(cls, parser: typing.Optional[ArgumentParser] = None) -> ArgumentParser:
        parser = super(FishTask, cls).gen_command_parser(parser)
        parser.add_argument("region")
        parser.add_argument("--fresh-water", action="store_true", dest="fresh_water")
        return parser

    def _perform_task(self) -> None:
        assert self.args is not None
        print(f"Fish! Region: {self.args.region}, Is Fresh Water: {self.args.fresh_water}")


class TestCliTask(unittest.TestCase):
    """Test for CliTask and gen_cli_parser"""

    def test_clitask_gen_command_parser_without_parent(self):
        parser = WormsTask.gen_command_parser()
        self.assertEqual(parser.prog, WormsTask.command)
        self.assertEqual(parser.description, WormsTask.description)

    def test_clitask_gen_command_parser_with_parent(self):
        parser = WormsTask.gen_command_parser()
        parser = ArthropodsTask.gen_command_parser(parser)
        self.assertEqual(parser.prog, WormsTask.command)
        self.assertEqual(parser.description, WormsTask.description)

    def test_clitask_run_command_all_args(self):
        with mock.patch.object(CliTask, "run", lambda self: self.args):
            argv = ["Lumbricus", "terrestris"]
            args = WormsTask.run_command(argv=argv)
            self.assertEqual("Lumbricus", args.genus)  # type: ignore[attr-defined]
            self.assertEqual("terrestris", args.species)  # type: ignore[attr-defined]

    def test_clitask_run_command_known_args(self):
        with mock.patch.object(CliTask, "run", lambda self: self.args):
            argv = ["Lumbricus", "terrestris", "--found-on", "land"]
            args = WormsTask.run_command(argv=argv, known_args=True)
            self.assertEqual("Lumbricus", args.genus)  # type: ignore[attr-defined]
            self.assertEqual("terrestris", args.species)  # type: ignore[attr-defined]

    def test_gen_cli_parser(self):
        root_parser = ArgumentParser(add_help=False)
        root_parser.add_argument(
            "--level",
            type=str,
            required=False,
            default="INFO",
            help="Logging level (default: %(default)s)",
            dest="log_level",
        )

        def print_help(_: Namespace) -> None:
            root_parser.print_help()

        root_parser.set_defaults(func=print_help)

        tests: typing.List[typing.Tuple[str, CliParserConfig, typing.List[str], Namespace]] = [
            ("Root parser only", {}, ["--level", "DEBUG"], Namespace(log_level="DEBUG", func=print_help)),
            (
                "Single subcommand, depth of 1",
                {WormsTask: {}},
                ["worms", "Lumbricus", "terrestris"],
                Namespace(
                    log_level="INFO",
                    genus="Lumbricus",
                    species="terrestris",
                    subcommand="worms",
                    func=WormsTask._CliTask__run_command,  # type: ignore[attr-defined] # pylint: disable=no-member,protected-access
                ),
            ),
            (
                "Single subcommand with alias, depth of 1",
                {WormsTask: {}},
                ["w", "Lumbricus", "terrestris"],
                Namespace(
                    log_level="INFO",
                    genus="Lumbricus",
                    species="terrestris",
                    subcommand="w",
                    func=WormsTask._CliTask__run_command,  # type: ignore[attr-defined] # pylint: disable=no-member,protected-access
                ),
            ),
            (
                "Multiple subcommands, depth of 1",
                {WormsTask: {}, ArthropodsTask: {}},
                ["--level", "WARNING", "arthropods", "Palaemonias", "ganteri"],
                Namespace(
                    log_level="WARNING",
                    genus="Palaemonias",
                    species="ganteri",
                    subcommand="arthropods",
                    func=ArthropodsTask._CliTask__run_command,  # type: ignore[attr-defined] # pylint: disable=no-member,protected-access
                ),
            ),
            (
                "Single subcommand, depth of 2, tuple without aliases",
                {("invertebrates", "Invertebrate animals"): {ArthropodsTask: {}}},
                ["invertebrates", "arthropods", "Neotibicen", "linnei"],
                Namespace(
                    log_level="INFO",
                    genus="Neotibicen",
                    species="linnei",
                    subcommand="arthropods",
                    func=ArthropodsTask._CliTask__run_command,  # type: ignore[attr-defined] # pylint: disable=no-member,protected-access
                ),
            ),
            (
                "Single subcommand, depth of 2, tuple with aliases",
                {(("invertebrates", "i"), "Invertebrate animals"): {ArthropodsTask: {}}},
                ["i", "arthropods", "Neotibicen", "linnei"],
                Namespace(
                    log_level="INFO",
                    genus="Neotibicen",
                    species="linnei",
                    subcommand="arthropods",
                    func=ArthropodsTask._CliTask__run_command,  # type: ignore[attr-defined] # pylint: disable=no-member,protected-access
                ),
            ),
            (
                "Multiple subcommands, depth of 2, tuple without aliases",
                {("invertebrates", "Invertebrate animals"): {WormsTask: {}, ArthropodsTask: {}}},
                ["invertebrates", "worms", "Lumbricus", "terrestris"],
                Namespace(
                    log_level="INFO",
                    genus="Lumbricus",
                    species="terrestris",
                    subcommand="worms",
                    func=WormsTask._CliTask__run_command,  # type: ignore[attr-defined] # pylint: disable=no-member,protected-access
                ),
            ),
            (
                "Multiple subcommands, depth of 2, tuple with aliases",
                {(("invertebrates", "i"), "Invertebrate animals"): {WormsTask: {}, ArthropodsTask: {}}},
                ["i", "worms", "Lumbricus", "terrestris"],
                Namespace(
                    log_level="INFO",
                    genus="Lumbricus",
                    species="terrestris",
                    subcommand="worms",
                    func=WormsTask._CliTask__run_command,  # type: ignore[attr-defined] # pylint: disable=no-member,protected-access
                ),
            ),
            (
                "Multiple subcommands, depth of 2, multiple tuples without aliases",
                {
                    ("invertebrates", "Invertebrate animals"): {
                        WormsTask: {},
                        ArthropodsTask: {},
                    },
                    ("vertebrates", "Vertebrate animals"): {
                        FishTask: {},
                    },
                },
                ["vertebrates", "fish", "Canada", "--fresh-water"],
                Namespace(
                    log_level="INFO",
                    region="Canada",
                    fresh_water=True,
                    subcommand="fish",
                    func=FishTask._CliTask__run_command,  # type: ignore[attr-defined] # pylint: disable=no-member,protected-access
                ),
            ),
            (
                "Multiple subcommands, depth of 2, multiple tuples with aliases",
                {
                    ("invertebrates", "Invertebrate animals"): {
                        WormsTask: {},
                        ArthropodsTask: {},
                    },
                    (("vertebrates", "v"), "Vertebrate animals"): {
                        FishTask: {},
                    },
                },
                ["v", "f", "Canada", "--fresh-water"],
                Namespace(
                    log_level="INFO",
                    region="Canada",
                    fresh_water=True,
                    subcommand="f",
                    func=FishTask._CliTask__run_command,  # type: ignore[attr-defined] # pylint: disable=no-member,protected-access
                ),
            ),
        ]

        with mock.patch.object(ArgumentParser, "exit"):
            for test_name, parser_config, argv, expected in tests:
                with self.subTest(test_name=test_name):
                    parser = ArgumentParser(prog="animals.py", description="CLI for animals", parents=[root_parser])
                    parser = gen_cli_parser(parser, parser_config)
                    args = parser.parse_args(args=argv)
                    self.assertEqual(expected, args)
