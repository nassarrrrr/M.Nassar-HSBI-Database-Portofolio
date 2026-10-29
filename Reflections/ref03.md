# Reflection 3: Module 3 (LLM-Assisted SQL & Query Profiling)

## Take-away: what do I want to remember?
- `EXPLAIN QUERY PLAN` shows *what* the database does; a stopwatch only shows *how long*. `SCAN` means every row is read; `SEARCH ... USING INDEX` means the index found the rows.
- An index is not automatically faster. It made the single-day lookup about 19× faster, but it made the dashboard about 5× slower, because the dashboard needs most of the rows anyway.
- A function around a column (`date(ordered_on)`, `lower(technician)`) or a leading wildcard (`LIKE '%ei%'`) stops the index from being used.
- Never build SQL by gluing text together. Bound parameters (`?`) are the only real fix for injection.

## AI verification: how did I check the LLM's SQL?
I asked ChatGPT for the city/revenue query and did not trust it until I had:
1. **Run it:** it runs, and the result is identical to the module's reference query.
2. **Checked correctness:** it uses `COUNT(DISTINCT customer_id)`, and the 2025 filter is a half-open range without a function around the column. Both are right.
3. **Looked for edge cases:** the inner joins would drop a city with no 2025 orders. That does not happen in this data, but the query would silently hide it.
4. **Profiled it:** the plan shows `SCAN ol` plus three primary-key `SEARCH`es and temp B-trees for grouping and sorting.

The LLM's suggestion to "add indexes to optimize" was the part I could disprove: I tested each index one at a time, and two of them made the query slower.

## What was good?
- One script ([run_module3.py](../Module03/run_module3.py)) runs the whole lab and saves all evidence, so the benchmark is repeatable.
- Seeing the injection payload return every customer made the danger very concrete.

## What was difficult, where did I struggle?
- Understanding why an index can make a query slower. It finally made sense once I saw how many rows the dashboard needs (40,575 of 60,000 orders).
- Reading the plan as a loop nest, and that SQLite chose to start from the biggest table.

## Was there any good struggling or exploration?
- My prediction that `LIKE 'Bei%'` would use the index was wrong. SQLite's `LIKE` ignores case, but the index does not.

## Interaction with peers and instructors
Task C (comparing plans and swapping curiosities with another pod) is still to be done in class.

## Help and extra work
I used an AI assistant (Claude) to explain the concepts and to write the script that runs the lab. Every claim in my notes is backed by the real output in [results.txt](../Module03/results.txt), which I produced on my own laptop.

## Status
Tasks A, B, 1, 2, 3 and 4 are done. Task C (pod exchange) is not yet done, and the window-function stretcher (Task 5) is skipped.
