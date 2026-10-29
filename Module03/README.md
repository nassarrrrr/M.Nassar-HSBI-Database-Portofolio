# Module 3: LLM-Assisted SQL & Query Profiling

## Learning goals
1. Build complex DQL queries: joins, aggregation with `GROUP BY`/`HAVING`, subqueries, and window functions.
2. Read `EXPLAIN QUERY PLAN` as primary evidence: say what the engine will do, tell a `SCAN` from a `SEARCH`, and a table lookup from a covering index.
3. Benchmark the effect of an index and explain when the planner ignores one.
4. Generate a query with an LLM, then verify it: correctness, performance, and edge cases.
5. Prevent SQL injection with bound parameters and demonstrate why string concatenation is exploitable.

## Files
- Setup (builds `warehouse.db`): [setup.sql](setup.sql)
- The whole lab in one run: [run_module3.py](run_module3.py). Run it from the repo root with `uv run python Module03/run_module3.py`
- All raw output (plans, timings, injection demo): [results.txt](results.txt)
- The LLM's query: [llm_query.sql](llm_query.sql)
- Injection drill: [injection_demo.py](injection_demo.py)
- Study notes and curiosities: [sql-notes.md](sql-notes.md)
- Reflection: [Reflection 3](../Reflections/ref03.md)

## Setup check
`warehouse.db` has 2,000 customers, 500 products, 60,000 orders and 240,000 order lines, as expected.

## Task 1: ask the LLM, then check the plan
**Prompt (ChatGPT):** "SQLite schema: customer(customer_id, name, city), product(product_id, sku, price), orders(order_id, customer_id, ordered_on, status), order_line(order_id, product_id, qty). Write a query that returns, for each city, the number of distinct customers and the total revenue (sum of qty*price) of orders placed in 2025, ordered by revenue descending."

**The LLM's SQL:** [llm_query.sql](llm_query.sql). It joins all four tables, filters `ordered_on >= '2025-01-01' AND ordered_on < '2026-01-01'`, groups by city and sorts by revenue.

**Predicted plan:** a `SCAN` of one big table, `SEARCH` by primary key on the others, and temp B-trees for the `GROUP BY` and `ORDER BY`, because no index supplies that order.

**Actual plan (no extra index):**
```
SCAN ol
SEARCH o USING INTEGER PRIMARY KEY (rowid=?)
SEARCH c USING INTEGER PRIMARY KEY (rowid=?)
SEARCH p USING INTEGER PRIMARY KEY (rowid=?)
USE TEMP B-TREE FOR GROUP BY
USE TEMP B-TREE FOR count(DISTINCT)
USE TEMP B-TREE FOR ORDER BY
```
Surprise: SQLite starts from `order_line` (the biggest table, 240,000 rows), not from `orders`, and reaches the other three tables through their primary keys.

**Correctness:**
- `COUNT(DISTINCT c.customer_id)` is right. A plain `COUNT(*)` would count order lines, not customers.
- The year filter is a half-open range (`>= 2025-01-01` and `< 2026-01-01`), so it includes 31 December and excludes 2026. It is also written without a function around the column, so an index on `ordered_on` *could* be used.
- The result is identical to the module's reference query: Bielefeld 11,242,176 · Gütersloh 8,422,344 · Münster 5,493,504 · Paderborn 2,815,656, each with 500 customers.
- **Edge case:** the inner joins drop a city whose customers placed no orders in 2025, so "for each city" is only true if every city has orders. Here all four do. To show such cities with 0, the join would need to be a `LEFT JOIN` with the date filter moved into the `ON` clause.

## Task 2: index benchmark (median of 3 runs)
| Step | Dashboard (ms) | Plan changed? | Single-day lookup (ms) |
|---|---|---|---|
| No extra index | 130.4 | `SCAN ol` | 2.895 (`SCAN o`) |
| + `ix_orders_ordered_on` | 127.4 | **No**, still `SCAN ol` | **0.152** (`SEARCH o USING INDEX ix_orders_ordered_on`) |
| + `ix_orderline_order` | **655.2** | **Yes**: now starts from `SEARCH o USING INDEX` and looks up `ol` by index | 0.208 |
| + `ix_orderline_product` | 607.0 | No | 0.155 |

The single-day lookup is batched 200 times per run, because one run is below the ~1 ms timer floor.

**What this shows:**
- **The index wins on the single-day lookup:** about 19× faster, and the plan changed from `SCAN o` to `SEARCH o USING INDEX`.
- **The indexes made the dashboard about 5× slower.** The dashboard needs about two thirds of all orders (40,575 of 60,000 are in 2025). With `ix_orderline_order`, the planner switches to an index-driven join: one index lookup per order instead of one straight pass over `order_line`. An index changes the plan; it does not guarantee a speedup.
- **`ix_orders_ordered_on` alone does not change the dashboard plan.** A filter that keeps most rows is not selective enough to be worth an index.
- **`ix_orderline_product` is useless *for this query*,** because `product` is reached through its primary key. But `SELECT COUNT(*) FROM order_line WHERE product_id = 42` uses it, even as a `COVERING INDEX`. So it is "useless for this query", not "useless".
- **A function defeats the index:** `WHERE date(o.ordered_on) = '2026-02-14'` is a `SCAN o` again, even with the index.

## Task 3: injection drill
Output of [injection_demo.py](injection_demo.py):
```
normal   : [(1, 'Customer 1')]
injected : [(1, 'Customer 1'), (2, 'Customer 2'), (3, 'Customer 3')] ...
safe     : []
apostrophe (vulnerable): crashed with near "Brien": syntax error
apostrophe (safe)      : []
```
- **Payload used:** `' OR '1'='1`. In the vulnerable version it closes the quote and adds a condition that is always true, so every customer is returned.
- **The story's crash:** the name `O'Brien` breaks the vulnerable query with a syntax error.
- **Why escaping `'` by hand is not a real fix:** quotes are only one way in. A value used as a number (`WHERE id = 5 OR 1=1`) needs no quote at all; identifiers such as table or column names follow different rules; encodings and the database's own escaping rules differ; and every developer has to remember it every time, so one forgotten place is enough. With bound parameters (`?`), the value is sent separately from the SQL text, so the database can never read it as SQL. The driver is responsible for correctness, not each programmer.

## Task 4: one query, from algebra to plan
For the dashboard query (with C = customer, O = orders, L = order_line, P = product):

γ city; COUNT(DISTINCT customer_id), SUM(qty·price) ( σ ordered_on ≥ '2025-01-01' ∧ ordered_on < '2026-01-01' ( C ⋈ O ⋈ L ⋈ P ) )

Then `ORDER BY` sorts the result (sorting is not part of classic relational algebra).
- **⋈** = the three `JOIN ... ON` clauses (customer_id, order_id, product_id)
- **σ** = the `WHERE` date range
- **γ** = `GROUP BY c.city` with the two aggregates
- **π** is implied by γ: only city, customers and revenue come out

The SQL matches the algebra: every operator appears exactly once. The plan executes it in a different order (it starts from L), which is allowed because joins can be reordered without changing the result.
