"""Database tools for the SQL Analyst Agent.

These LangChain-compatible tools connect to any SQLAlchemy-supported database
(SQLite, PostgreSQL, MySQL, SQL Server, …) via a DATABASE_URL connection string.
The default is a local SQLite file suitable for the bundled demo dataset.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any

import sqlalchemy as sa
from langchain_core.tools import tool

_ROW_LIMIT = 500
_DEFAULT_DB_URL = os.getenv("DATABASE_URL", "sqlite:///data/ecommerce.db")


def _strip_sql_comments(sql: str) -> str:
    """Remove block and line SQL comments, then strip surrounding whitespace."""
    no_block = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    no_line = re.sub(r"--.*?$", "", no_block, flags=re.MULTILINE)
    return no_line.strip()


def _make_engine(db_url: str) -> sa.Engine:
    """Create a short-lived SQLAlchemy engine for a single tool call."""
    return sa.create_engine(db_url, pool_pre_ping=True)


@tool
def execute_query(sql: str, db_url: str = _DEFAULT_DB_URL) -> dict[str, Any]:
    """Execute a read-only SELECT query against any SQLAlchemy-compatible database.

    The connection target is controlled by the ``db_url`` parameter (a standard
    SQLAlchemy connection URL). Set the ``DATABASE_URL`` environment variable to
    change the default without touching the call site.

    Returns a dict with keys:
      - ``rows``: list of row dicts (max 500)
      - ``columns``: list of column names
      - ``row_count``: number of rows returned (≤ 500)
      - ``truncated``: True when the result set was capped at 500 rows
      - ``execution_ms``: wall-clock query time in milliseconds
      - ``error`` / ``error_type``: present only when the query fails
    """
    cleaned = _strip_sql_comments(sql)
    if not cleaned.lower().startswith("select"):
        raise ValueError(
            "Only SELECT statements are allowed. "
            "Provide a query that begins with SELECT."
        )

    started = time.perf_counter()
    try:
        engine = _make_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(sa.text(sql))
            columns = list(result.keys())
            fetched = result.fetchmany(_ROW_LIMIT + 1)
            truncated = len(fetched) > _ROW_LIMIT
            rows = [dict(row._mapping) for row in fetched[:_ROW_LIMIT]]
        engine.dispose()
    except Exception as exc:  # noqa: BLE001
        execution_ms = round((time.perf_counter() - started) * 1000, 3)
        return {
            "error": str(exc),
            "error_type": type(exc).__name__,
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
def get_schema(db_url: str = _DEFAULT_DB_URL) -> dict[str, Any]:
    """Return schema metadata and approximate row counts for all user-visible tables.

    Works with any SQLAlchemy-supported database. Pass ``db_url`` (a standard
    SQLAlchemy connection URL) to target a specific database; defaults to
    ``DATABASE_URL`` from the environment or the bundled SQLite demo file.

    Returns a dict with keys:
      - ``tables``: mapping of table name → list of column descriptors
        (``column``, ``type``, ``pk``, ``nullable``)
      - ``approximate_row_counts``: mapping of table name → integer row count
      - ``dialect``: the SQLAlchemy dialect name (e.g. "sqlite", "postgresql")
      - ``error`` / ``error_type``: present only when introspection fails
    """
    try:
        engine = _make_engine(db_url)
        inspector = sa.inspect(engine)
        dialect_name: str = engine.dialect.name

        tables: dict[str, list[dict[str, Any]]] = {}
        approximate_row_counts: dict[str, int] = {}

        for table_name in inspector.get_table_names():
            pk_cols = set(
                inspector.get_pk_constraint(table_name).get("constrained_columns", [])
            )
            col_infos = inspector.get_columns(table_name)
            columns = [
                {
                    "column": col["name"],
                    "type": str(col["type"]),
                    "pk": col["name"] in pk_cols,
                    "nullable": bool(col.get("nullable", True)),
                }
                for col in col_infos
            ]
            tables[table_name] = columns

            # Use a SQLAlchemy table clause so the identifier is quoted by the
            # dialect — never interpolate user-visible names into raw SQL text.
            tbl = sa.table(table_name)
            with engine.connect() as conn:
                count = conn.execute(
                    sa.select(sa.func.count()).select_from(tbl)
                ).scalar()
                approximate_row_counts[table_name] = int(count or 0)

        engine.dispose()
    except Exception as exc:  # noqa: BLE001
        return {
            "error": str(exc),
            "error_type": type(exc).__name__,
            "tables": {},
            "approximate_row_counts": {},
            "dialect": "",
        }

    return {
        "tables": tables,
        "approximate_row_counts": approximate_row_counts,
        "dialect": dialect_name,
    }
