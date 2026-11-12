# Module 6a: DuckDB notes

All numbers are from my own run: [results.txt](results.txt). Summary tables: [README.md](README.md).

## Round 1: build
- **Why exactly 2,000,000 rows?** The history is Module 5's 200,000-row `report_jobpart`, copied for k = 0 … 9 (10 quarters) with the date shifted by `k × 91` days. 10 × 200,000 = 2,000,000.
- **Why 91 days and not 90?** 91 days is exactly 13 weeks, so every copy keeps the same weekday pattern. With 90 days, the copies would drift by one weekday each quarter.
- **`'+91 days'` vs `'+1 month'`:** `+1 month` depends on which month it starts from (28–31 days), so shifted dates could bunch up or skip days. A fixed day count is predictable.

## Round 2: convert
- Same data or just the same size? I compared **row count and `SUM(part_price)`** on both sides: 2,000,000 rows and 21,000,000.0 on both. A file size alone would prove nothing; a checksum of the column values does.
- **The Parquet is about 47× smaller** (2.40 MB vs 112.65 MB), because it stores each column together and compresses repeated values: there are only 50 machines, 10 parts and 7 technicians.

## Round 3: the race
- **The bug:** SQLite's `strftime(format, date)` and DuckDB's `strftime(date, format)` take their arguments in opposite order. The module's monthly query returned NULL months in SQLite. **The timing looked great, but it compared a wrong answer with a right one.**
- **Fair race:** dashboard 85×, monthly 102× in DuckDB's favour.
- **My prediction was wrong** about `date_trunc`: I expected it to be faster, as the module says, but on my laptop it was slower (47.6 vs 25.6 ms).
- **SQLite wins** a point query on an index: one day took 1.9 ms in SQLite with an index on `done_on`, and 4.0 ms in DuckDB.

## Round 4: the plan
- **The line that proves the column store read less:** `TABLE_SCAN … Projections: machine_id, site, technician, part_price`, 2,000,000 rows. Four of seven columns.
- **The dominating operator:** `HASH_GROUP_BY` with 0.12 s, grouping 2,000,000 rows into 350.
- **Which plan to show a manager?** DuckDB's `EXPLAIN ANALYZE`, because it is a measurement with real row counts and times. SQLite's `EXPLAIN QUERY PLAN` is a prediction, useful for checking whether an index will be used before running anything.

## Round 5: the boundary
**"For Kortmann, DuckDB is the wrong engine when"** the application writes or reads one row per request: 1,000 inserts took 3.6 ms in SQLite and 1,085.6 ms in DuckDB; 1,000 lookups took 2.1 ms and 518.4 ms. `executemany` only brought DuckDB's inserts down to 744.8 ms. The fix is in the design, not the engine: collect the rows and load them in bulk, for example the nightly Parquet rebuild.

## Round 6: memo to Lea Winter and Yasmin Kaya
> **To: Lea Winter (controlling) and Yasmin Kaya (operations)**
>
> Move the month-end and history reports to a Parquet copy read by DuckDB; keep all daily writes and single-machine lookups in SQLite. On two and a half years of history (2,000,000 rows), the monthly report took 2,607 ms in SQLite and 25.6 ms in DuckDB, about 100× faster, and the dashboard 2,508 ms against 29.5 ms. The copy is a single 2.4 MB file (1.4 MB with zstd), against 112.7 MB for the SQLite table, and it gives the same answer: 2,000,000 rows and a total of 21,000,000.0 on both sides. The copy is rebuilt by `refresh.py` in about 8 seconds, run nightly after the shift; `--check` compares the row count and the total with SQLite and fails loudly on a mismatch. If the copy goes stale, the report silently misses the newest jobs, so the refresh's output line, with its date and checksum, should be logged and checked every morning. We would not move the operational writes: 1,000 single inserts took 3.6 ms in SQLite but 1,086 ms in DuckDB, and one-day lookups with an index are faster in SQLite (1.9 ms against 4.0 ms).
>
> **What `--check` protects against, and what it does not:** it catches a copy that lost or duplicated rows or changed prices, because the count or the total would differ. It does not catch a copy that is correct but old, if SQLite itself was not updated, and it would miss two errors that cancel out in the sum. A date check (the newest `done_on` on both sides) would close the first gap.

## Curiosities
- The same function name, `strftime`, takes its arguments in opposite order in the two engines, and SQLite answers NULL instead of raising an error.
- The Parquet file is 47× smaller than the SQLite table, with the same rows.
- In DuckDB, grouping took longer than reading 2,000,000 rows.
- Refresh is idempotent down to the byte: 2,460,682 bytes both times.
