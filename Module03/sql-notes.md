# Module 3: SQL notes

## 1. References I used (and the concept each taught me)
| Source | Concept I understood best from it |
|---|---|
| [sqlite.org/eqp.html](https://www.sqlite.org/eqp.html) | How to read `EXPLAIN QUERY PLAN`: one line per table, read as a loop nest |
| [Wikipedia: Relational algebra](https://en.wikipedia.org/wiki/Relational_algebra) | σ = WHERE, π = SELECT list, ⋈ = JOIN, γ = GROUP BY |
| [Use The Index, Luke](https://use-the-index-luke.com/) | Why a function or a leading wildcard stops an index from being used |
| [OWASP SQL Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html) | Bound parameters are the primary defence, not escaping |

## 2. Plan vocabulary (my one-line definitions)
- **SCAN:** every row of the table is read.
- **SEARCH ... USING INDEX:** the index finds the matching rows, then SQLite still fetches each row from the table.
- **COVERING INDEX:** the index already holds everything the query needs, so the table is never opened.
- **USE TEMP B-TREE:** SQLite had to sort or group by itself, because no index gave the order.

## 3. Clause order
SQL is *written* `SELECT … FROM … WHERE … GROUP BY … HAVING … ORDER BY`, but *evaluated* `FROM → WHERE → GROUP BY → HAVING → SELECT → ORDER BY`.
**Counterexample:** `SELECT qty * price AS total FROM … WHERE total > 100` should fail in standard SQL, because `WHERE` runs before `SELECT` creates the alias. (SQLite is lenient and often accepts it, which hides the mistake until the query moves to another database.)

## 4. Task A: plan safari (on Module02/legacy.db)
Raw output: [results.txt](results.txt), section TASK A.

| Query | Expected | Before index | After `ix_job_tech` |
|---|---|---|---|
| `technician = 'Beier'` | SCAN, then SEARCH | SCAN | **SEARCH USING INDEX ix_job_tech** |
| `machine_name = 'cnc-02'` | SCAN (no index on machine) | SCAN | SCAN (the index is on another table) |
| `technician LIKE '%ei%'` | SCAN | SCAN | SCAN (leading wildcard) |

**Breaking the index on purpose:**
- `lower(technician) = 'beier'` → SCAN. A function around the column hides it from the index.
- **My wrong prediction:** I expected `technician LIKE 'Bei%'` (no leading wildcard) to use the index. It is still a SCAN. SQLite's `LIKE` is case-insensitive by default, but the index is case-sensitive, so the index cannot answer it.

## 5. Task B: algebra check
My algebra for `SELECT * FROM maint_job WHERE technician = 'Beier'`:
σ technician = 'Beier' (maint_job), with no π because `SELECT *` keeps every column.

**LLM comparison (Claude):** it gave the same expression. For the dashboard query (see the [README, Task 4](README.md#task-4-one-query-from-algebra-to-plan)), the interesting difference is `ORDER BY` and `COUNT(DISTINCT)`: classic relational algebra has no sorting, so `ORDER BY` sits outside the expression.

## 6. Remarkable things and curiosities
- **An index made a query 5× slower** (dashboard: 125.9 ms → 602.1 ms). The plan changed, but for the worse. Source: [README, Task 2](README.md#task-2-index-benchmark-median-of-3-runs).
- **The biggest table is scanned first:** the dashboard plan starts with `SCAN ol` (240,000 rows), not with `orders`.
- **Same customers, very different revenue:** every city has exactly 500 customers, but Bielefeld earns 4× more than Paderborn. The generated ids line up (`x % 2000`, `x % 500`), so some cities always get the expensive products. Generated data has patterns that real data would not.
- **Setup question 4:** `date('2025-01-01', '+' || (x % 540) || ' days')`. The modifier must be a text like `'+42 days'`, so it is built with `||`. When x = 540, `x % 540` = 0, so the date is 2025-01-01 again. The latest date is 2026-06-24.
- **Setup question 1:** no table has 240,000 rows. `WITH RECURSIVE` generates the numbers 1, 2, 3, … by itself.
- **I don't know yet:** why `USE TEMP B-TREE FOR count(DISTINCT)` appears as its own line.

## 7. Task C: share with another pod
*Not yet. To do with a neighbouring pod: compare plans (check `sqlite3 --version` first) and swap curiosities.*
