from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ccw.init import init_local_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ccw")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create repo-local CCW state")
    init_parser.add_argument("path", nargs="?", default=".", help="Init target path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            init_local_state(Path(args.path))
            return 0
    except (FileNotFoundError, NotADirectoryError, PermissionError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    parser.error(f"unknown command: {args.command}")
