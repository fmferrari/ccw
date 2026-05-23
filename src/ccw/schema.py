from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_TABLES = ("files", "symbols", "edges", "facts", "episodes")

FILES_TABLE_COLUMNS = ("id", "path", "content_hash", "size_bytes", "language")

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
    except sqlite3.Error as error:
        if created_database and path.exists():
            path.unlink()
        raise ValueError(f"Failed to bootstrap index schema: {path}") from error

    return path


def _ensure_files_table(connection: sqlite3.Connection) -> None:
    column_names = tuple(_read_table_columns(connection, "files"))

    if set(FILES_TABLE_COLUMNS).issubset(column_names):
        return

    if column_names != ("id",):
        raise ValueError("Unexpected files table schema")

    connection.executescript(
        """
        DROP TABLE files;
        CREATE TABLE files (
            id INTEGER PRIMARY KEY,
            path TEXT NOT NULL UNIQUE,
            content_hash TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            language TEXT NOT NULL
        );
        """
    )


def _read_table_columns(connection: sqlite3.Connection, table_name: str) -> list[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()

    return [name for _, name, *_ in rows]
