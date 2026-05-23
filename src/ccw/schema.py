from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA_TABLES = ("files", "symbols", "edges", "facts", "episodes")

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
    except sqlite3.Error as error:
        if created_database and path.exists():
            path.unlink()
        raise ValueError(f"Failed to bootstrap index schema: {path}") from error

    return path
