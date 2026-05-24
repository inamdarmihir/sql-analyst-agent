<div align="center">

# 🧠 SQL Analyst Agent

**Conversational SQL analytics on any database — powered by Deep Agents + LangGraph**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python)](https://www.python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-≥0.5-green?logo=langchain)](https://github.com/langchain-ai/langgraph)
[![Deep Agents](https://img.shields.io/badge/deepagents-≥0.6-purple)](https://pypi.org/project/deepagents)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-≥2.0-red)](https://www.sqlalchemy.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## Overview

SQL Analyst Agent is a **plug-and-play conversational analytics agent** that connects to any relational database and answers natural-language questions using SQL. It is built on the **Deep Agents interpreter pattern**: all intermediate query results are stored in a QuickJS interpreter sandbox — never in model context — and narrative analysis is delegated to sub-agents via Programmatic Tool Calling (PTC).

```
User question
     │
     ▼
┌──────────────────────────────────────────────────────────────┐
│                        Root Agent                            │
│                                                              │
│  1. get_schema()          ← dialect-aware schema introspect  │
│  2. execute_query(sql)    ← rows stay in interpreter state   │
│  3. tools.task(…)         ← narrative delegated to sub-agent │
│  4. write_file(report)    ← persist to virtual filesystem    │
│                                                              │
│  ┌────────────────────┐   ┌─────────────────────────────┐   │
│  │  QuickJS Sandbox   │   │     Sub-agent (PTC)         │   │
│  │  – query results   │   │  – narrative per data slice │   │
│  │  – computations    │   │  – 2-3 sentence summaries   │   │
│  │  – aggregations    │   └─────────────────────────────┘   │
│  └────────────────────┘                                      │
└──────────────────────────────────────────────────────────────┘
     │
     ▼
Final synthesised report (no raw rows in model context)
```

### Why the interpreter pattern?

Large result sets sent directly to the model waste context, hit token limits, and slow down responses. With the interpreter pattern:

- **Raw rows stay in the sandbox** — only summaries and computed values surface to the model.
- **Code runs at the edge** — aggregations and joins happen in TypeScript inside QuickJS, not in another LLM call.
- **Sub-agents handle narrative** — each data slice is explained by a focused sub-agent, keeping the root model's context small and its reasoning precise.

---

## Supported Databases

| Database | Connection URL format | Extra driver |
|---|---|---|
| **SQLite** *(default)* | `sqlite:///path/to/db.sqlite` | — built-in |
| **PostgreSQL** | `postgresql+psycopg2://user:pass@host:5432/db` | `[postgres]` |
| **MySQL / MariaDB** | `mysql+pymysql://user:pass@host:3306/db` | `[mysql]` |
| **SQL Server** | `mssql+pyodbc://user:pass@host:1433/db?driver=ODBC+Driver+18+for+SQL+Server` | `[mssql]` |
| **CockroachDB** | `cockroachdb+psycopg2://user:pass@host:26257/db` | `[postgres]` |
| **DuckDB** | `duckdb:///path/to/file.duckdb` | `duckdb-engine` |

All connection strings are standard **SQLAlchemy URLs** — any engine that SQLAlchemy supports will work.

---

## Quick Start

### Prerequisites

- Python ≥ 3.11
- [`uv`](https://docs.astral.sh/uv/) package manager
- An [Anthropic API key](https://console.anthropic.com) (or swap to another provider — see below)

### 1. Install

```bash
# Core dependencies (includes SQLite driver — no extras needed for the demo)
uv sync

# PostgreSQL
uv sync --extra postgres

# MySQL / MariaDB
uv sync --extra mysql

# SQL Server
uv sync --extra mssql

# All drivers
uv sync --extra all-drivers
```

### 2. Configure

```bash
cp .env.example .env
```

Open `.env` and set at minimum:

```env
ANTHROPIC_API_KEY=sk-ant-...

# Use the bundled SQLite demo (default):
DATABASE_URL=sqlite:///data/ecommerce.db

# Or point to your own database:
# DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/mydb
```

### 3. Seed demo data *(SQLite only)*

```bash
uv run python seed_data.py
```

This creates `data/ecommerce.db` with 2 000 customers, 200 products, 15 000 orders and 40 000 order-items across the last 24 months. Running it again is safe — the script is fully idempotent.

Skip this step when pointing `DATABASE_URL` at an existing database.

### 4. Launch

```bash
langgraph dev
```

Open **LangGraph Studio** at the URL printed in the terminal.

---

## Example Questions

Paste any of these into LangGraph Studio to see the agent in action:

| Category | Question |
|---|---|
| Aggregation | *"Which region had the highest revenue last quarter?"* |
| Cohort analysis | *"How does order value change over a customer's first 6 months?"* |
| Anomaly detection | *"Which products have unusually high return rates compared to their category average?"* |
| Multi-hop | *"Are gold-tier customers from the South ordering more in the evenings?"* |
| Trend | *"Show me month-over-month revenue growth for the last 12 months broken down by customer tier."* |

---

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(required)* | API key for Anthropic. Swap the key when using a different provider. |
| `DATABASE_URL` | `sqlite:///data/ecommerce.db` | SQLAlchemy connection URL for the target database. |
| `MODEL` | `anthropic:claude-sonnet-4-6` | LangChain model string passed to `create_deep_agent`. |

---

## Swapping the Model Provider

Change the `MODEL` environment variable (or the `model=` string in `agent.py`) to any provider string supported by LangChain:

```env
# Anthropic (default)
MODEL=anthropic:claude-sonnet-4-6

# OpenAI
MODEL=openai:gpt-4o

# Google Gemini
MODEL=google-genai:gemini-2.0-flash
```

Install the matching `langchain-<provider>` package and set the provider's API key in `.env`.

---

## Connecting to Your Database

1. Install the appropriate driver extra (see table above).
2. Set `DATABASE_URL` in `.env` to your connection string.
3. Start the agent — it will call `get_schema()` automatically before writing any SQL.

No code changes are required. The agent detects the SQL dialect from the connection URL and adapts its query syntax accordingly.

---

## Repository Structure

```
sql-analyst-agent/
├── agent.py          # LangGraph graph entry point (exports `agent`)
├── seed_data.py      # Idempotent e-commerce demo data seeder
├── langgraph.json    # LangGraph server configuration
├── pyproject.toml    # Project metadata and dependencies
├── .env.example      # Environment variable template
├── tools/
│   ├── __init__.py
│   └── sql_tools.py  # execute_query + get_schema (SQLAlchemy-backed)
└── data/
    └── .gitkeep      # seed_data.py writes ecommerce.db here
```

---

## Extending the Agent

### Add a new tool

1. Implement a LangChain `@tool` function (in `tools/` or a new module).
2. Import it in `agent.py` and add it to `tools=[...]` inside `create_deep_agent(...)`.
3. Add the tool name to `CodeInterpreterMiddleware(ptc=[...])` so the interpreter can call it programmatically.
4. Describe when and how to use it in `SYSTEM_PROMPT`.

### Example: add a `visualise` tool

```python
# tools/viz_tools.py
from langchain_core.tools import tool

@tool
def visualise(data: list[dict], chart_type: str = "bar") -> str:
    """Render a simple ASCII chart from a list of row dicts."""
    ...
```

```python
# agent.py
from tools.viz_tools import visualise

agent = create_deep_agent(
    tools=[execute_query, get_schema, visualise],
    middleware=[
        FilesystemMiddleware(),
        CodeInterpreterMiddleware(
            ptc=["execute_query", "get_schema", "visualise", "write_file", "read_file", "task"],
            ...
        ),
    ],
)
```

---

## How It Works — The Interpreter Pattern

The agent uses [Deep Agents](https://pypi.org/project/deepagents) with a `CodeInterpreterMiddleware` backed by QuickJS. When the model writes TypeScript code in its response, the middleware executes it in the sandbox and returns only the final expression value to the model.

**Data flow:**

1. The model writes TypeScript that calls `tools.executeQuery(...)`.
2. The middleware intercepts the `tools.*` call, runs the Python tool, and injects the result as a variable in the sandbox.
3. The TypeScript code aggregates, filters, and transforms the data — all inside the sandbox.
4. Only the final computed value (a summary string or small object) leaves the sandbox and enters model context.
5. For each data slice that requires narrative explanation, the TypeScript code calls `tools.task(...)` to spin up a focused sub-agent.

This means **the model never sees raw database rows** — it only sees schema metadata, computed summaries, and sub-agent outputs.

---

## License

MIT — see [LICENSE](LICENSE).
