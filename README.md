# sql-analyst-agent

This repository demonstrates an interpreter-first Deep Agents pattern for SQL analytics: the agent writes and runs SQL in the QuickJS interpreter, stores all intermediate query results in interpreter variables, and only sends compact reasoning outputs (not raw rows) back through model context. Narrative analysis of specific result slices is delegated through programmatic tool calling (`tools.task`) to sub-agents, and the root agent synthesizes a final report.

## Setup

```bash
uv sync
cp .env.example .env  # add ANTHROPIC_API_KEY
uv run python seed_data.py
langgraph dev
```

## Example questions

1. Aggregation: "Which region had the highest revenue last quarter?"
2. Cohort analysis: "How does order value change over a customer's first 6 months?"
3. Anomaly: "Which products have unusually high return rates compared to their category average?"
4. Multi-hop: "Are gold-tier customers from the South ordering more in the evenings?"
5. Trend: "Show me month-over-month revenue growth for the last 12 months broken down by tier."

## Swap to a different model provider

In `agent.py`, change the `model=` string in `create_deep_agent(...)`. For example, switch from Anthropic to another provider/model string supported by your LangChain + Deep Agents setup.

## Extend with a new tool and expose it via PTC

1. Add a new `@tool` function (for example in `tools/sql_tools.py` or another module).
2. Import and include it in `tools=[...]` inside `create_deep_agent(...)`.
3. Add the tool name to `CodeInterpreterMiddleware(ptc=[...])` so interpreter code can invoke it programmatically.
4. Update the system prompt guidance with when and how the interpreter should use that tool.
