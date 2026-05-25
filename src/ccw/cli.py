from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ccw.classify import classify as classify_text
from ccw.compile import do_compile
from ccw.episodes import add_episode
from ccw.facts import add_fact
from ccw.index import index_repository
from ccw.init import init_local_state
from ccw.session import prepare_session_bundle
from ccw.validate import validate_compiled_artifact


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

    compile_parser = subparsers.add_parser("compile", help="Compile task-scoped context artifact")
    compile_parser.add_argument("--task", required=True, help="Task description text")
    compile_parser.add_argument("--budget", type=int, default=None, help="Override token budget")
    compile_parser.add_argument("--out", type=Path, default=None, help="Output artifact path")
    compile_parser.add_argument("--mode", default=None, help="Explicit classification mode (skip auto-classify)")
    compile_parser.add_argument("path", nargs="?", default=".", help="Compile target path")

    session_parser = subparsers.add_parser("session", help="Manage portable session bundles")
    session_subparsers = session_parser.add_subparsers(dest="session_command", required=True)

    session_prepare_parser = session_subparsers.add_parser("prepare", help="Prepare a portable session bundle")
    session_prepare_parser.add_argument("--task", required=True, help="Task description text")
    session_prepare_parser.add_argument("--budget", type=int, default=None, help="Override token budget")
    session_prepare_parser.add_argument("--out-dir", type=Path, default=None, help="Session bundle output directory")
    session_prepare_parser.add_argument("--mode", default=None, help="Explicit classification mode (skip auto-classify)")
    session_prepare_parser.add_argument("path", nargs="?", default=".", help="Session target path")

    validate_parser = subparsers.add_parser("validate", help="Validate a compiled context artifact")
    validate_parser.add_argument("artifact", type=Path, help="Compiled artifact path to validate")
    validate_parser.add_argument("path", nargs="?", default=".", help="Target repository path")

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
        if args.command == "compile":
            output_path = do_compile(
                target=Path(args.path),
                task_description=args.task,
                output_path=args.out,
                mode=args.mode,
                budget=args.budget,
            )
            print(f"Compiled context written to: {output_path}")
            return 0
        if args.command == "session" and args.session_command == "prepare":
            bundle_dir = prepare_session_bundle(
                target=Path(args.path),
                task_description=args.task,
                output_dir=args.out_dir,
                mode=args.mode,
                budget=args.budget,
            )
            print(f"Session bundle written to: {bundle_dir}")
            return 0
        if args.command == "validate":
            from ccw.init import require_initialized_local_state, resolve_target_directory

            resolved_target = resolve_target_directory(Path(args.path), description="Validate target")

            database_path = None
            try:
                database_path = require_initialized_local_state(resolved_target)
            except ValueError:
                pass

            errors = validate_compiled_artifact(
                artifact_path=args.artifact,
                database_path=database_path,
            )

            if errors:
                for error in errors:
                    print(f"Error: {error}", file=sys.stderr)
                return 1
            print("Valid compiled artifact")
            return 0
    except (FileNotFoundError, NotADirectoryError, PermissionError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    parser.error(f"unknown command: {args.command}")
