from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ccw.classify import classify as classify_text
from ccw.episodes import add_episode
from ccw.facts import add_fact
from ccw.index import index_repository
from ccw.init import init_local_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ccw")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create repo-local CCW state")
    init_parser.add_argument("path", nargs="?", default=".", help="Init target path")

    index_parser = subparsers.add_parser("index", help="Build deterministic repo inventory")
    index_parser.add_argument("path", nargs="?", default=".", help="Index target path")

    facts_parser = subparsers.add_parser("facts", help="Manage explicit project facts")
    facts_subparsers = facts_parser.add_subparsers(dest="facts_command", required=True)

    facts_add_parser = facts_subparsers.add_parser("add", help="Append one explicit fact")
    facts_add_parser.add_argument("kind", help="Fact kind")
    facts_add_parser.add_argument("text", help="Fact text")
    facts_add_parser.add_argument("path", nargs="?", default=".", help="Fact target path")

    episodes_parser = subparsers.add_parser("episodes", help="Manage explicit completed-run episodes")
    episodes_subparsers = episodes_parser.add_subparsers(dest="episodes_command", required=True)

    episodes_add_parser = episodes_subparsers.add_parser("add", help="Append one explicit episode")
    episodes_add_parser.add_argument("summary", help="Episode summary")
    episodes_add_parser.add_argument("touched_files", help="Comma-separated touched files")
    episodes_add_parser.add_argument("path", nargs="?", default=".", help="Episode target path")

    classify_parser = subparsers.add_parser("classify", help="Classify a task description into a deterministic mode")
    classify_parser.add_argument("text", help="Task description text")
    classify_parser.add_argument("path", nargs="?", default=".", help="Classify target path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init":
            init_local_state(Path(args.path))
            return 0
        if args.command == "index":
            index_repository(Path(args.path))
            return 0
        if args.command == "facts" and args.facts_command == "add":
            add_fact(Path(args.path), args.kind, args.text)
            return 0
        if args.command == "episodes" and args.episodes_command == "add":
            add_episode(Path(args.path), args.summary, args.touched_files)
            return 0
        if args.command == "classify":
            mode = classify_text(Path(args.path), args.text)
            print(mode)
            return 0
    except (FileNotFoundError, NotADirectoryError, PermissionError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    parser.error(f"unknown command: {args.command}")
