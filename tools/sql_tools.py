from __future__ import annotations

import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

_ROW_LIMIT = 500


def _strip_sql_comments(sql: str) -> str:
    no_block_comments = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    no_line_comments = re.sub(r"--.*?$", "", no_block_comments, flags=re.MULTILINE)
    return no_line_comments.strip()


@tool
def execute_query(sql: str, db_path: str = "data/ecommerce.db") -> dict[str, Any]:
    """Execute a read-only SQLite SELECT query and return rows with metadata."""
    cleaned = _strip_sql_comments(sql)
    if not cleaned.lower().startswith("select"):
        raise ValueError(
            "Only SELECT statements are allowed. Provide a query that starts with SELECT."
        )

    started = time.perf_counter()
    try:
        with sqlite3.connect(Path(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(sql)
            columns = [description[0] for description in (cursor.description or [])]
            fetched = cursor.fetchmany(_ROW_LIMIT + 1)
            truncated = len(fetched) > _ROW_LIMIT
            rows = [dict(row) for row in fetched[:_ROW_LIMIT]]
    except sqlite3.OperationalError as exc:
        execution_ms = round((time.perf_counter() - started) * 1000, 3)
        return {
            "error": str(exc),
            "error_type": "OperationalError",
            "rows": [],
            "columns": [],
            "row_count": 0,
            "truncated": False,
            "execution_ms": execution_ms,
        }

    execution_ms = round((time.perf_counter() - started) * 1000, 3)
    return {
        "rows": rows,
        "columns": columns,
        "row_count": len(rows),
        "truncated": truncated,
        "execution_ms": execution_ms,
    }


@tool
def get_schema(db_path: str = "data/ecommerce.db") -> dict[str, Any]:
    """Return schema metadata and approximate row counts for all non-system tables."""
    tables: dict[str, list[dict[str, Any]]] = {}
    approximate_row_counts: dict[str, int] = {}

    with sqlite3.connect(Path(db_path)) as conn:
        table_rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        for (table_name,) in table_rows:
            info = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            columns = []
            for column in info:
                columns.append(
                    {
                        "column": column[1],
                        "type": column[2],
                        "pk": bool(column[5]),
                        "nullable": not bool(column[3]),
                    }
                )
            tables[table_name] = columns
            approximate_row_counts[table_name] = conn.execute(
                f"SELECT COUNT(*) FROM {table_name}"
            ).fetchone()[0]

    return {
        "tables": tables,
        "approximate_row_counts": approximate_row_counts,
    }
