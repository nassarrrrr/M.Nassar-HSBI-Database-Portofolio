# Reflection 6a: Module 6a (The Analytical Engine, DuckDB)

## Take-away: what do I want to remember?
- A column store (Parquet + DuckDB) reads only the columns a query needs. On 2,000,000 rows, the monthly report went from 2.6 s in SQLite to 25.6 ms in DuckDB.
- Check that both engines give the **same answer** before timing them. The module's monthly race compared a wrong SQLite answer (NULL months) with a right DuckDB one.
- DuckDB is not "better": for one row at a time, SQLite was about 300× faster on inserts and 250× faster on lookups.
- An analytical copy is only useful if it stays fresh and someone checks it: `refresh.py --check`.

## What was good?
- Seeing a 112 MB table become a 2.4 MB Parquet file with exactly the same total.
- The `EXPLAIN ANALYZE` output with real row counts per operator.

## What was difficult, where did I struggle?
- Understanding why the scan reads 2,000,000 rows but only 4 of the 7 columns.
- Reading DuckDB's plan bottom-up.

## Was there any good struggling or exploration?
- The strftime argument order: SQLite returned NULL instead of an error, so the wrong answer was silent.
- `date_trunc` made DuckDB slower on my laptop, the opposite of the module's prediction.
- Making SQLite win: with an index, a one-day query was faster in SQLite (1.9 ms) than in DuckDB (4.0 ms).

## Interaction with peers and instructors
The round discussions with the nearest pod are still to be done in class.

## Help and extra work
I used an AI assistant (Claude) to explain the concepts and to write the runner and `refresh.py`. All numbers come from my own run in [results.txt](../Module06a/results.txt).

## Status
Rounds 1–6, the zstd homework and the intense track (`refresh.py` with two `--check` runs) are done. The pod discussions are still open.
