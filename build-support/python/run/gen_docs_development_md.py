import re
from argparse import ArgumentParser, Namespace
from pathlib import Path


def gen_development_md(args: Namespace) -> int:
    source_path: Path = args.source_path
    target_path: Path = args.target_path

    if not source_path.is_file():
        raise FileNotFoundError(str(source_path))
    if not target_path.parent.is_dir():
        target_path.parent.mkdir(parents=True, exist_ok=True)

    content = source_path.read_text()
    content = re.sub(r"(\[[^\]]+\])\((?!http|#)([^\)]+)\)", r"\1(../../\2)", content)
    target_path.write_text(content)

    return 0


def gen_command_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Generate DEVELOPMENT.md with patched repository paths for the docs")
    parser.add_argument("source_path", type=Path, help="Path to DEVELOPMENT.md file")
    parser.add_argument("target_path", type=Path, help="Paht to write patched file")
    parser.set_defaults(func=gen_development_md)
    return parser


def main() -> int:
    parser = gen_command_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    main()
