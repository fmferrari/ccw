from __future__ import annotations

import ast
import hashlib
import io
import json
import os
import posixpath
import re
import shutil
import sqlite3
import subprocess
import tokenize
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath

from ccw.init import require_initialized_local_state, resolve_target_directory
from ccw.schema import bootstrap_index_database


EXCLUDED_DIRECTORY_NAMES = {
    ".ccw",
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".tox",
    ".eggs",
    "node_modules",
    "bower_components",
    "build",
    "dev-dist",
    "dist",
    "out",
    ".next",
    ".nuxt",
    ".svelte-kit",
    "coverage",
    ".nyc_output",
    "htmlcov",
    ".cache",
    ".parcel-cache",
    ".turbo",
    "target",
    # Browser automation / test artifact directories
    "browser-data",
    ".playwright-profile",
    "playwright-report",
    "test-results",
    # Common large-data / log directories
    "logs",
    ".logs",
    "tmp",
    ".tmp",
    # Harness runtime state
    ".openclaw",
}
SNAPSHOT_FILE_NAME = "index.json"

LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".md": "markdown",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
}

SCRIPT_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx")

SCRIPT_DECLARATION_RE = re.compile(
    r"^(export\s+)?(?:(default)\s+)?(?:(async)\s+)?(class|function|const|let|var)\s+([A-Za-z_$][\w$]*)"
)
SCRIPT_IMPORT_FROM_RE = re.compile(r'^import\s+.+?\s+from\s+["\']([^"\']+)["\']\s*;?\s*$')
SCRIPT_IMPORT_SIDE_EFFECT_RE = re.compile(r'^import\s+["\']([^"\']+)["\']\s*;?\s*$')
SCRIPT_EXPORT_FROM_RE = re.compile(r'^export\s*{\s*([^}]+)\s*}\s*from\s*["\']([^"\']+)["\']\s*;?\s*$')
SCRIPT_EXPORT_ALL_FROM_RE = re.compile(r'^export\s+\*\s+from\s+["\']([^"\']+)["\']\s*;?\s*$')
SCRIPT_EXPORT_NAMED_RE = re.compile(r'^export\s*{\s*([^}]+)\s*}\s*;?\s*$')


@dataclass(frozen=True)
class SourceFile:
    path: str
    absolute_path: Path
    language: str
    content_hash: str
    file_bytes: bytes


@dataclass(frozen=True)
class GitSignal:
    last_commit_at: int | None
    last_author_email: str | None
    owner_email: str | None
    owner_commit_count: int | None


@dataclass(frozen=True)
class FileRecord:
    path: str
    content_hash: str
    size_bytes: int
    language: str
    last_commit_at: int | None
    last_author_email: str | None
    owner_email: str | None
    owner_commit_count: int | None


@dataclass(frozen=True)
class SymbolRecord:
    file_path: str
    name: str
    kind: str
    line: int
    end_line: int
    export_name: str | None


@dataclass(frozen=True)
class EdgeRecord:
    source_path: str
    kind: str
    target_path: str
    detail: str | None
    line: int | None


@dataclass(frozen=True)
class ArtifactRecord:
    file_path: str
    kind: str
    title: str
    search_text: str


def index_repository(target: Path) -> Path:
    resolved_target = resolve_target_directory(target, description="Index target")
    database_path = require_initialized_local_state(resolved_target)
    snapshot_path = database_path.parent / "snapshots" / SNAPSHOT_FILE_NAME
    backup_path = database_path.with_suffix(f"{database_path.suffix}.bak")

    file_records, symbol_records, edge_records, artifact_records = _collect_index_records(resolved_target)
    snapshot_text = _render_snapshot(file_records, symbol_records, edge_records, artifact_records)
    snapshot_bytes = snapshot_path.read_bytes() if snapshot_path.exists() else None
    shutil.copy2(database_path, backup_path)

    try:
        bootstrap_index_database(database_path)
        _replace_index_records(database_path, file_records, symbol_records, edge_records, artifact_records)
        _write_snapshot(snapshot_path, snapshot_text)
    except Exception:
        shutil.copy2(backup_path, database_path)
        _restore_snapshot(snapshot_path, snapshot_bytes)
        raise
    finally:
        if backup_path.exists():
            backup_path.unlink()

    return database_path


def _collect_index_records(
    target: Path,
) -> tuple[list[FileRecord], list[SymbolRecord], list[EdgeRecord], list[ArtifactRecord]]:
    source_files = _collect_source_files(target)
    known_paths = {source_file.path for source_file in source_files}
    git_signals = _collect_git_signals(target, source_files)

    file_records = [_file_record(source_file, git_signals.get(source_file.path)) for source_file in source_files]
    symbol_records: list[SymbolRecord] = []
    edge_records: list[EdgeRecord] = []
    artifact_records: list[ArtifactRecord] = []

    for source_file in source_files:
        if source_file.language == "python":
            file_symbols, file_edges = _collect_python_records(source_file, known_paths)
            symbol_records.extend(file_symbols)
            edge_records.extend(file_edges)
        elif source_file.language in {"typescript", "javascript"}:
            file_symbols, file_edges = _collect_script_records(source_file, known_paths)
            symbol_records.extend(file_symbols)
            edge_records.extend(file_edges)

        artifact_record = _collect_document_artifact(source_file)
        if artifact_record is not None:
            artifact_records.append(artifact_record)

    edge_records.extend(_collect_test_edges(source_files, edge_records))

    return (
        sorted(file_records, key=lambda record: record.path),
        sorted(symbol_records, key=lambda record: (record.file_path, record.line, record.name, record.kind)),
        _sorted_unique_edges(edge_records),
        sorted(artifact_records, key=lambda record: record.file_path),
    )


def _collect_source_files(target: Path) -> list[SourceFile]:
    source_files: list[SourceFile] = []

    for root, directory_names, file_names in os.walk(target, topdown=True):
        root_path = Path(root)
        directory_names[:] = [
            directory_name
            for directory_name in sorted(directory_names)
            if not _is_excluded_directory_name(directory_name) and not (root_path / directory_name).is_symlink()
        ]

        for file_name in sorted(file_names):
            file_path = root_path / file_name
            if file_path.is_symlink() or not file_path.is_file():
                continue

            relative_path = file_path.relative_to(target).as_posix()
            file_bytes = file_path.read_bytes()
            source_files.append(
                SourceFile(
                    path=relative_path,
                    absolute_path=file_path,
                    language=_detect_language(file_path),
                    content_hash=hashlib.sha256(file_bytes).hexdigest(),
                    file_bytes=file_bytes,
                )
            )

    return source_files


def _is_excluded_directory_name(directory_name: str) -> bool:
    if directory_name in EXCLUDED_DIRECTORY_NAMES:
        return True
    return directory_name.endswith(".egg-info")


def _file_record(source_file: SourceFile, git_signal: GitSignal | None) -> FileRecord:
    signal = git_signal or GitSignal(None, None, None, None)

    return FileRecord(
        path=source_file.path,
        content_hash=source_file.content_hash,
        size_bytes=len(source_file.file_bytes),
        language=source_file.language,
        last_commit_at=signal.last_commit_at,
        last_author_email=signal.last_author_email,
        owner_email=signal.owner_email,
        owner_commit_count=signal.owner_commit_count,
    )


def _detect_language(path: Path) -> str:
    return LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "unknown")


def _collect_python_records(source_file: SourceFile, known_paths: set[str]) -> tuple[list[SymbolRecord], list[EdgeRecord]]:
    module = _parse_python_module(source_file.path, source_file.file_bytes)
    explicit_exports = _python_explicit_exports(module.body)
    symbol_records = [
        symbol_record
        for symbol_record in (_python_symbol_record(source_file.path, node, explicit_exports) for node in module.body)
        if symbol_record is not None
    ]

    return symbol_records, _python_import_edges(source_file.path, module.body, known_paths)


def _parse_python_module(relative_path: str, file_bytes: bytes) -> ast.Module:
    try:
        encoding, _ = tokenize.detect_encoding(io.BytesIO(file_bytes).readline)
        return ast.parse(file_bytes.decode(encoding), filename=relative_path)
    except (LookupError, SyntaxError, UnicodeDecodeError) as error:
        raise ValueError(f"Invalid Python syntax in {relative_path}") from error


def _python_explicit_exports(nodes: list[ast.stmt]) -> set[str] | None:
    explicit_exports: set[str] | None = None
    for node in nodes:
        if isinstance(node, ast.Assign):
            target_names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_names = [node.target.id]
        else:
            continue

        if "__all__" not in target_names:
            continue

        literal_exports = _literal_string_collection(node.value)
        if literal_exports is not None:
            explicit_exports = literal_exports

    return explicit_exports


def _literal_string_collection(node: ast.AST | None) -> set[str] | None:
    if node is None or not isinstance(node, (ast.List, ast.Tuple)):
        return None

    values: set[str] = set()
    for element in node.elts:
        if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
            return None
        values.add(element.value)

    return values


def _python_symbol_record(relative_path: str, node: ast.stmt, explicit_exports: set[str] | None) -> SymbolRecord | None:
    if isinstance(node, ast.ClassDef):
        kind = "class"
    elif isinstance(node, ast.AsyncFunctionDef):
        kind = "async_function"
    elif isinstance(node, ast.FunctionDef):
        kind = "function"
    else:
        return None

    export_name = _python_export_name(node.name, explicit_exports)

    return SymbolRecord(
        file_path=relative_path,
        name=node.name,
        kind=kind,
        line=node.lineno,
        end_line=getattr(node, "end_lineno", node.lineno),
        export_name=export_name,
    )


def _python_export_name(name: str, explicit_exports: set[str] | None) -> str | None:
    if explicit_exports is not None:
        return name if name in explicit_exports else None
    if name.startswith("_"):
        return None
    return name


def _python_import_edges(relative_path: str, nodes: list[ast.stmt], known_paths: set[str]) -> list[EdgeRecord]:
    edge_records: list[EdgeRecord] = []

    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                target_path = _resolve_python_module_name(alias.name, known_paths)
                if target_path is not None:
                    edge_records.append(
                        EdgeRecord(
                            source_path=relative_path,
                            kind="import",
                            target_path=target_path,
                            detail=alias.name,
                            line=node.lineno,
                        )
                    )
        elif isinstance(node, ast.ImportFrom):
            base_parts = _resolve_python_import_from_base(relative_path, node)
            module_spec = "." * node.level + (node.module or "")
            if base_parts is None:
                continue

            module_target = _resolve_python_module_parts(base_parts, known_paths)
            for alias in node.names:
                alias_parts = base_parts + alias.name.split(".")
                alias_target = _resolve_python_module_parts(alias_parts, known_paths)
                target_path = alias_target or module_target
                if target_path is not None:
                    edge_records.append(
                        EdgeRecord(
                            source_path=relative_path,
                            kind="import",
                            target_path=target_path,
                            detail=module_spec,
                            line=node.lineno,
                        )
                    )

    return edge_records


def _resolve_python_import_from_base(relative_path: str, node: ast.ImportFrom) -> list[str] | None:
    path_parts = list(PurePosixPath(relative_path).parts)
    if node.level == 0:
        base_parts: list[str] = []
    else:
        package_parts = path_parts[:-1]
        trim_count = node.level - 1
        if trim_count > len(package_parts):
            return None
        base_parts = package_parts[: len(package_parts) - trim_count]

    if node.module:
        base_parts += node.module.split(".")

    return base_parts


def _resolve_python_module_name(module_name: str, known_paths: set[str]) -> str | None:
    return _resolve_python_module_parts(module_name.split("."), known_paths)


def _resolve_python_module_parts(module_parts: list[str], known_paths: set[str]) -> str | None:
    module_path = "/".join(module_parts)
    if not module_path:
        return None

    file_candidate = f"{module_path}.py"
    if file_candidate in known_paths:
        return file_candidate

    package_candidate = f"{module_path}/__init__.py"
    if package_candidate in known_paths:
        return package_candidate

    return None


def _collect_script_records(source_file: SourceFile, known_paths: set[str]) -> tuple[list[SymbolRecord], list[EdgeRecord]]:
    try:
        script_text = source_file.file_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"Invalid {source_file.language} source in {source_file.path}") from error

    symbol_records: list[SymbolRecord] = []
    edge_records: list[EdgeRecord] = []
    pending_exports: dict[str, str] = {}

    for line_number, raw_line in enumerate(script_text.splitlines(), start=1):
        if raw_line.startswith((" ", "\t")):
            continue

        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue

        named_export_from_match = SCRIPT_EXPORT_FROM_RE.match(line)
        if named_export_from_match is not None:
            module_spec = named_export_from_match.group(2)
            target_path = _resolve_relative_module(source_file.path, module_spec, known_paths)
            if target_path is not None:
                edge_records.append(
                    EdgeRecord(
                        source_path=source_file.path,
                        kind="re_export",
                        target_path=target_path,
                        detail=module_spec,
                        line=line_number,
                    )
                )
            continue

        export_all_match = SCRIPT_EXPORT_ALL_FROM_RE.match(line)
        if export_all_match is not None:
            module_spec = export_all_match.group(1)
            target_path = _resolve_relative_module(source_file.path, module_spec, known_paths)
            if target_path is not None:
                edge_records.append(
                    EdgeRecord(
                        source_path=source_file.path,
                        kind="re_export",
                        target_path=target_path,
                        detail=module_spec,
                        line=line_number,
                    )
                )
            continue

        import_match = SCRIPT_IMPORT_FROM_RE.match(line) or SCRIPT_IMPORT_SIDE_EFFECT_RE.match(line)
        if import_match is not None:
            module_spec = import_match.group(1)
            target_path = _resolve_relative_module(source_file.path, module_spec, known_paths)
            if target_path is not None:
                edge_records.append(
                    EdgeRecord(
                        source_path=source_file.path,
                        kind="import",
                        target_path=target_path,
                        detail=module_spec,
                        line=line_number,
                    )
                )
            continue

        declaration_match = SCRIPT_DECLARATION_RE.match(line)
        if declaration_match is not None:
            exported = declaration_match.group(1) is not None
            default_export = declaration_match.group(2) is not None
            is_async = declaration_match.group(3) is not None
            declaration_kind = declaration_match.group(4)
            symbol_name = declaration_match.group(5)
            symbol_records.append(
                SymbolRecord(
                    file_path=source_file.path,
                    name=symbol_name,
                    kind=_script_symbol_kind(declaration_kind, is_async),
                    line=line_number,
                    end_line=line_number,
                    export_name="default" if default_export else (symbol_name if exported else None),
                )
            )
            continue

        named_export_match = SCRIPT_EXPORT_NAMED_RE.match(line)
        if named_export_match is not None:
            for local_name, export_name in _parse_named_exports(named_export_match.group(1)):
                pending_exports.setdefault(local_name, export_name)

    return _apply_script_named_exports(symbol_records, pending_exports), edge_records


def _script_symbol_kind(declaration_kind: str, is_async: bool) -> str:
    if declaration_kind == "class":
        return "class"
    if declaration_kind == "function":
        return "async_function" if is_async else "function"
    return "variable"


def _parse_named_exports(export_clause: str) -> list[tuple[str, str]]:
    exports: list[tuple[str, str]] = []
    for raw_part in export_clause.split(","):
        part = raw_part.strip()
        if not part:
            continue
        if " as " in part:
            local_name, export_name = [segment.strip() for segment in part.split(" as ", 1)]
        else:
            local_name = part
            export_name = part
        exports.append((local_name, export_name))
    return exports


def _apply_script_named_exports(
    symbol_records: list[SymbolRecord],
    pending_exports: dict[str, str],
) -> list[SymbolRecord]:
    if not pending_exports:
        return symbol_records

    updated_records: list[SymbolRecord] = []
    for symbol_record in symbol_records:
        export_name = symbol_record.export_name or pending_exports.get(symbol_record.name)
        updated_records.append(
            SymbolRecord(
                file_path=symbol_record.file_path,
                name=symbol_record.name,
                kind=symbol_record.kind,
                line=symbol_record.line,
                end_line=symbol_record.end_line,
                export_name=export_name,
            )
        )
    return updated_records


def _resolve_relative_module(source_path: str, module_spec: str, known_paths: set[str]) -> str | None:
    if not module_spec.startswith("."):
        return None

    source_parent = PurePosixPath(source_path).parent
    candidate_path = posixpath.normpath(f"{source_parent.as_posix()}/{module_spec}")

    if PurePosixPath(candidate_path).suffix:
        return candidate_path if candidate_path in known_paths else None

    for extension in SCRIPT_EXTENSIONS:
        extended_candidate = f"{candidate_path}{extension}"
        if extended_candidate in known_paths:
            return extended_candidate

    for extension in SCRIPT_EXTENSIONS:
        index_candidate = f"{candidate_path}/index{extension}"
        if index_candidate in known_paths:
            return index_candidate

    return None


def _collect_document_artifact(source_file: SourceFile) -> ArtifactRecord | None:
    if source_file.language not in {"markdown", "json", "yaml"}:
        return None

    text = source_file.file_bytes.decode("utf-8")
    title = _artifact_title(source_file.path, source_file.language, text)
    search_text = _artifact_search_text(source_file.language, text)

    return ArtifactRecord(
        file_path=source_file.path,
        kind=source_file.language,
        title=title,
        search_text=search_text,
    )


def _artifact_title(path: str, language: str, text: str) -> str:
    if language == "markdown":
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip() or Path(path).stem
    return Path(path).stem


def _artifact_search_text(language: str, text: str) -> str:
    if language == "json":
        try:
            normalized_json = json.dumps(json.loads(text), sort_keys=True, separators=(",", ":"))
        except json.JSONDecodeError:
            normalized_json = text
        return _normalize_search_text(normalized_json)

    return _normalize_search_text(text)


def _normalize_search_text(text: str) -> str:
    return " ".join(text.split())


def _collect_git_signals(target: Path, source_files: list[SourceFile]) -> dict[str, GitSignal]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=target,
            text=True,
            capture_output=True,
            check=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return {}

    git_root = Path(result.stdout.strip())
    git_paths_by_source_path: dict[str, str] = {}

    for source_file in source_files:
        try:
            git_relative_path = source_file.absolute_path.relative_to(git_root).as_posix()
        except ValueError:
            continue

        git_paths_by_source_path[source_file.path] = git_relative_path

    if not git_paths_by_source_path:
        return {}

    try:
        target_pathspec = target.relative_to(git_root).as_posix()
    except ValueError:
        target_pathspec = "."
    if target_pathspec == ".":
        target_pathspec = "."

    return _collect_git_signals_from_log(git_root, target_pathspec, git_paths_by_source_path)


def _collect_git_signals_from_log(
    git_root: Path,
    target_pathspec: str,
    git_paths_by_source_path: dict[str, str],
) -> dict[str, GitSignal]:
    source_paths_by_git_path = {git_path: source_path for source_path, git_path in git_paths_by_source_path.items()}

    try:
        result = subprocess.run(
            ["git", "log", "--format=%ct%x00%ae", "--name-only", "--", target_pathspec],
            cwd=git_root,
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return {}

    latest_by_source_path: dict[str, tuple[int, str]] = {}
    owners_by_source_path: dict[str, Counter[str]] = {}
    current_commit: tuple[int, str] | None = None

    for line in result.stdout.splitlines():
        if not line:
            continue
        if "\x00" in line:
            raw_timestamp, raw_author = line.split("\x00", 1)
            try:
                current_commit = (int(raw_timestamp), raw_author)
            except ValueError:
                current_commit = None
            continue
        if current_commit is None:
            continue

        source_path = source_paths_by_git_path.get(line)
        if source_path is None:
            continue

        latest_by_source_path.setdefault(source_path, current_commit)
        owners_by_source_path.setdefault(source_path, Counter())[current_commit[1]] += 1

    signals: dict[str, GitSignal] = {}
    for source_path, (last_commit_at, last_author_email) in latest_by_source_path.items():
        owner_counts = owners_by_source_path[source_path]
        owner_email, owner_commit_count = sorted(owner_counts.items(), key=lambda item: (-item[1], item[0]))[0]
        signals[source_path] = GitSignal(
            last_commit_at=last_commit_at,
            last_author_email=last_author_email,
            owner_email=owner_email,
            owner_commit_count=owner_commit_count,
        )

    return signals


def _collect_test_edges(source_files: list[SourceFile], import_edges: list[EdgeRecord]) -> list[EdgeRecord]:
    non_test_paths = [source_file.path for source_file in source_files if not _is_test_file(source_file.path)]
    import_targets_by_source: dict[str, set[str]] = {}
    for edge_record in import_edges:
        if edge_record.kind != "import":
            continue
        import_targets_by_source.setdefault(edge_record.source_path, set()).add(edge_record.target_path)

    test_edges: list[EdgeRecord] = []
    for source_file in source_files:
        if not _is_test_file(source_file.path):
            continue

        mapping = _unambiguous_test_target(source_file.path, non_test_paths, import_targets_by_source)
        if mapping is not None:
            target_path, detail = mapping
            test_edges.append(
                EdgeRecord(
                    source_path=source_file.path,
                    kind="tests",
                    target_path=target_path,
                    detail=detail,
                    line=None,
                )
            )

    return test_edges


def _unambiguous_test_target(
    test_path: str,
    non_test_paths: list[str],
    import_targets_by_source: dict[str, set[str]],
) -> tuple[str, str] | None:
    naming_candidates = _naming_test_candidates(test_path, non_test_paths)
    import_targets = sorted(import_targets_by_source.get(test_path, set()))
    import_candidates = [target_path for target_path in import_targets if target_path in non_test_paths]

    if len(import_candidates) > 1:
        return None

    if len(import_candidates) == 1:
        import_target = import_candidates[0]
        if len(naming_candidates) == 0 or len(naming_candidates) > 1 or naming_candidates[0] == import_target:
            return import_target, "import"
        return None

    if len(naming_candidates) == 1:
        return naming_candidates[0], "naming"

    return None


def _naming_test_candidates(test_path: str, non_test_paths: list[str]) -> list[str]:
    normalized_test_stem = _normalized_test_stem(test_path)
    if normalized_test_stem is None:
        return []

    return sorted(
        path for path in non_test_paths if _normalized_source_stem(path) == normalized_test_stem
    )


def _normalized_test_stem(path: str) -> str | None:
    pure_path = PurePosixPath(path)
    stem = pure_path.stem
    if stem.startswith("test_"):
        return stem[5:]
    if stem.endswith("_test"):
        return stem[:-5]
    if stem.endswith(".test"):
        return stem[:-5]
    if stem.endswith(".spec"):
        return stem[:-5]
    return None


def _normalized_source_stem(path: str) -> str:
    pure_path = PurePosixPath(path)
    if pure_path.name == "__init__.py":
        return pure_path.parent.name
    return pure_path.stem


def _is_test_file(path: str) -> bool:
    pure_path = PurePosixPath(path)
    if "tests" in pure_path.parts:
        return True

    stem = pure_path.stem
    return stem.startswith("test_") or stem.endswith("_test") or stem.endswith(".test") or stem.endswith(".spec")


def _sorted_unique_edges(edge_records: list[EdgeRecord]) -> list[EdgeRecord]:
    unique_records: dict[tuple[str, str, str, str | None, int | None], EdgeRecord] = {}
    for edge_record in edge_records:
        unique_records[(edge_record.source_path, edge_record.kind, edge_record.target_path, edge_record.detail, edge_record.line)] = edge_record

    return sorted(
        unique_records.values(),
        key=lambda record: (record.source_path, record.kind, record.target_path, record.line or 0, record.detail or ""),
    )


def _replace_index_records(
    database_path: Path,
    file_records: list[FileRecord],
    symbol_records: list[SymbolRecord],
    edge_records: list[EdgeRecord],
    artifact_records: list[ArtifactRecord],
) -> None:
    try:
        with sqlite3.connect(database_path) as connection:
            connection.execute("DELETE FROM artifacts")
            connection.execute("DELETE FROM edges")
            connection.execute("DELETE FROM symbols")
            connection.execute("DELETE FROM files")
            connection.executemany(
                (
                    "INSERT INTO files ("
                    "path, content_hash, size_bytes, language, last_commit_at, last_author_email, owner_email, owner_commit_count"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                ),
                [
                    (
                        record.path,
                        record.content_hash,
                        record.size_bytes,
                        record.language,
                        record.last_commit_at,
                        record.last_author_email,
                        record.owner_email,
                        record.owner_commit_count,
                    )
                    for record in file_records
                ],
            )
            connection.executemany(
                "INSERT INTO symbols (file_path, name, kind, line, end_line, export_name) VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (record.file_path, record.name, record.kind, record.line, record.end_line, record.export_name)
                    for record in symbol_records
                ],
            )
            connection.executemany(
                "INSERT INTO edges (source_path, kind, target_path, detail, line) VALUES (?, ?, ?, ?, ?)",
                [
                    (record.source_path, record.kind, record.target_path, record.detail, record.line)
                    for record in edge_records
                ],
            )
            connection.executemany(
                "INSERT INTO artifacts (file_path, kind, title, search_text) VALUES (?, ?, ?, ?)",
                [(record.file_path, record.kind, record.title, record.search_text) for record in artifact_records],
            )
    except sqlite3.Error as error:
        raise ValueError(f"Failed to persist index inventory: {database_path}") from error


def _render_snapshot(
    file_records: list[FileRecord],
    symbol_records: list[SymbolRecord],
    edge_records: list[EdgeRecord],
    artifact_records: list[ArtifactRecord],
) -> str:
    snapshot = {
        "artifacts": [asdict(record) for record in artifact_records],
        "edges": [asdict(record) for record in edge_records],
        "files": [asdict(record) for record in file_records],
        "symbols": [asdict(record) for record in symbol_records],
    }
    return json.dumps(snapshot, indent=2, sort_keys=True) + "\n"


def _write_snapshot(snapshot_path: Path, snapshot_text: str) -> None:
    temporary_path = snapshot_path.with_suffix(f"{snapshot_path.suffix}.tmp")
    temporary_path.write_text(snapshot_text, encoding="utf-8")
    temporary_path.replace(snapshot_path)


def _restore_snapshot(snapshot_path: Path, snapshot_bytes: bytes | None) -> None:
    temporary_path = snapshot_path.with_suffix(f"{snapshot_path.suffix}.tmp")
    if temporary_path.exists():
        temporary_path.unlink()

    if snapshot_bytes is None:
        if snapshot_path.exists():
            snapshot_path.unlink()
        return

    snapshot_path.write_bytes(snapshot_bytes)
