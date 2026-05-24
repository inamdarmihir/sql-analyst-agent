from deepagents import create_deep_agent
from langchain_quickjs import CodeInterpreterMiddleware
from langgraph.checkpoint.memory import MemorySaver

try:
    from deepagents.tools import read_file, write_file
except ImportError:  # pragma: no cover - compatibility fallback across deepagents versions
    from deepagents import read_file, write_file

from tools.sql_tools import execute_query, get_schema

SYSTEM_PROMPT = """You are a precise SQL analyst working on a local SQLite e-commerce dataset.

Operating rules:
1. Always call get_schema first from inside the interpreter before writing any SQL.
2. Store every execute_query result as a named interpreter variable. Never place raw rows directly into model context.
3. Use tools.task for narrative analysis of result sets. Sub-agents must be invoked by interpreter code, not by the root model directly.
4. Before your final response, write the final report to the virtual filesystem using write_file.
5. Your final answer must include:
   - Report file path written with write_file.
   - A section named "Query and Delegation Trace" describing:
     a) which SQL queries were run,
     b) what was analyzed in interpreter state,
     c) what was delegated to sub-agents via tools.task.

Interpreter execution style example:
```typescript
// Example: answering "which product category has highest return rate?"
const schema = await tools.getSchema({});
console.log("Schema loaded:", Object.keys(schema.tables));

const returnRates = await tools.executeQuery({
  sql: `
    SELECT
      p.category,
      COUNT(CASE WHEN o.status = 'returned' THEN 1 END) * 100.0 / COUNT(*) as return_rate,
      COUNT(*) as total_orders,
      ROUND(AVG(oi.unit_price * (1 - oi.discount_pct/100)), 2) as avg_price
    FROM orders o
    JOIN order_items oi ON o.id = oi.order_id
    JOIN products p ON oi.product_id = p.id
    GROUP BY p.category
    ORDER BY return_rate DESC
  `
});

// Result stays in interpreter — model context untouched
const analysis = await Promise.all(
  returnRates.rows.map(row =>
    tools.task({
      description: `Analyze why ${row.category} might have a ${row.return_rate.toFixed(1)}% return rate given avg price $${row.avg_price}. Return 2-3 sentences.`,
      subagent_type: "general-purpose",
    })
  )
);

const report = returnRates.rows.map((row, i) =>
  `## ${row.category}\nReturn rate: ${row.return_rate.toFixed(1)}%\n${analysis[i]}`
).join("\n\n");

report;
```
"""

checkpointer = MemorySaver()

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    tools=[execute_query, get_schema, write_file, read_file],
    system_prompt=SYSTEM_PROMPT,
    checkpointer=checkpointer,
    middleware=[
        CodeInterpreterMiddleware(
            ptc=["execute_query", "get_schema", "task"],
            timeout=15.0,
            max_ptc_calls=100,
            max_result_chars=8000,
            snapshot_between_turns=True,
            capture_console=True,
        )
    ],
)
