from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_TABLES = ("files", "symbols", "edges", "artifacts", "facts", "episodes")

FILES_REQUIRED_COLUMNS = ("id", "path", "content_hash", "size_bytes", "language")
FILES_OPTIONAL_COLUMNS = (
    ("last_commit_at", "INTEGER"),
    ("last_author_email", "TEXT"),
    ("owner_email", "TEXT"),
    ("owner_commit_count", "INTEGER"),
)
SYMBOLS_REQUIRED_COLUMNS = ("id", "file_path", "name", "kind", "line", "end_line")
SYMBOLS_OPTIONAL_COLUMNS = (("export_name", "TEXT"),)
EDGES_COLUMNS = ("id", "source_path", "kind", "target_path", "detail", "line")
ARTIFACTS_COLUMNS = ("id", "file_path", "kind", "title", "search_text")

SCHEMA_SQL = "\n".join(
    [
        "BEGIN;",
        *(f"CREATE TABLE IF NOT EXISTS {table_name} (id INTEGER PRIMARY KEY);" for table_name in SCHEMA_TABLES),
        "COMMIT;",
    ]
)


def bootstrap_index_database(path: Path) -> Path:
    if path.exists() and not path.is_file():
        raise ValueError(f"Index database path exists as a directory: {path}")

    created_database = not path.exists()

    try:
        with sqlite3.connect(path) as connection:
            connection.executescript(SCHEMA_SQL)
            _ensure_files_table(connection)
            _ensure_symbols_table(connection)
            _ensure_edges_table(connection)
            _ensure_artifacts_table(connection)
    except sqlite3.Error as error:
        if created_database and path.exists():
            path.unlink()
        raise ValueError(f"Failed to bootstrap index schema: {path}") from error

    return path


def _ensure_files_table(connection: sqlite3.Connection) -> None:
    column_names = tuple(_read_table_columns(connection, "files"))

    if column_names == ("id",):
        connection.executescript(
            """
            DROP TABLE files;
            CREATE TABLE files (
                id INTEGER PRIMARY KEY,
                path TEXT NOT NULL UNIQUE,
                content_hash TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                language TEXT NOT NULL,
                last_commit_at INTEGER,
                last_author_email TEXT,
                owner_email TEXT,
                owner_commit_count INTEGER
            );
            """
        )
        return

    if not set(FILES_REQUIRED_COLUMNS).issubset(column_names):
        raise ValueError("Unexpected files table schema")

    _ensure_optional_columns(connection, "files", column_names, FILES_OPTIONAL_COLUMNS)


def _ensure_symbols_table(connection: sqlite3.Connection) -> None:
    column_names = tuple(_read_table_columns(connection, "symbols"))

    if column_names == ("id",):
        connection.executescript(
            """
            DROP TABLE symbols;
            CREATE TABLE symbols (
                id INTEGER PRIMARY KEY,
                file_path TEXT NOT NULL,
                name TEXT NOT NULL,
                kind TEXT NOT NULL,
                line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                export_name TEXT
            );
            """
        )
        return

    if not set(SYMBOLS_REQUIRED_COLUMNS).issubset(column_names):
        raise ValueError("Unexpected symbols table schema")

    _ensure_optional_columns(connection, "symbols", column_names, SYMBOLS_OPTIONAL_COLUMNS)


def _ensure_edges_table(connection: sqlite3.Connection) -> None:
    column_names = tuple(_read_table_columns(connection, "edges"))

    if column_names == EDGES_COLUMNS:
        return

    if column_names != ("id",):
        raise ValueError("Unexpected edges table schema")

    connection.executescript(
        """
        DROP TABLE edges;
        CREATE TABLE edges (
            id INTEGER PRIMARY KEY,
            source_path TEXT NOT NULL,
            kind TEXT NOT NULL,
            target_path TEXT NOT NULL,
            detail TEXT,
            line INTEGER
        );
        """
    )


def _ensure_artifacts_table(connection: sqlite3.Connection) -> None:
    column_names = tuple(_read_table_columns(connection, "artifacts"))

    if column_names == ARTIFACTS_COLUMNS:
        return

    if column_names != ("id",):
        raise ValueError("Unexpected artifacts table schema")

    connection.executescript(
        """
        DROP TABLE artifacts;
        CREATE TABLE artifacts (
            id INTEGER PRIMARY KEY,
            file_path TEXT NOT NULL,
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            search_text TEXT NOT NULL
        );
        """
    )


def _ensure_optional_columns(
    connection: sqlite3.Connection,
    table_name: str,
    column_names: tuple[str, ...],
    optional_columns: tuple[tuple[str, str], ...],
) -> None:
    for column_name, column_type in optional_columns:
        if column_name in column_names:
            continue
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


def _read_table_columns(connection: sqlite3.Connection, table_name: str) -> list[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()

    return [name for _, name, *_ in rows]
