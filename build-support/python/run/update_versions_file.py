import json
from argparse import ArgumentParser, Namespace
from pathlib import Path


def update_versions_file(args: Namespace) -> int:
    source_path: Path = args.source_path
    docs_root_path = Path(__file__).resolve().parents[3].joinpath("docs")
    version: str = args.version

    # Ensure versions.json and docs root exist
    if not source_path.is_file():
        raise FileNotFoundError(str(source_path))
    if not docs_root_path.is_dir():
        raise FileNotFoundError(str(docs_root_path))

    # Ensure version is prepended with 'v'
    if not version.startswith("v"):
        version = f"v{version}"
    # Create the documentation version directory if it doesn't already exist
    docs_version_path = docs_root_path.joinpath(version)
    docs_version_path.mkdir(exist_ok=True)

    # Find the latest version and create symlink `latest`
    latest_version_path = [dir_path for dir_path in sorted(docs_root_path.glob("v*")) if dir_path.is_dir()][
        0
    ].relative_to(docs_root_path)
    latest_link_path = docs_root_path.joinpath("latest")
    if latest_link_path.is_symlink():
        latest_link_path.unlink()
    latest_link_path.symlink_to(latest_version_path, target_is_directory=True)

    # Make paths relative to repo root
    docs_version_path = docs_version_path.relative_to(docs_root_path)
    latest_link_path = latest_link_path.relative_to(docs_root_path)

    versions_map = json.loads(source_path.read_text())
    versions_map[version] = str(docs_version_path)
    versions_map["latest"] = str(latest_link_path)
    source_path.write_text(json.dumps(versions_map, indent=2))

    return 0


def gen_command_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Update documentation versions file with new version.")
    parser.add_argument("source_path", type=Path, help="Path to versions.json file")
    parser.add_argument("version", help="Version to add")
    parser.set_defaults(func=update_versions_file)
    return parser


def main() -> int:
    parser = gen_command_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    main()
