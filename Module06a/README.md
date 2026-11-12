# Module 6a: The Analytical Engine (DuckDB)

## Learning goals
1. Move a table out of SQLite into Parquet reproducibly, from a script.
2. Run the same aggregate in SQLite and DuckDB and report the difference honestly (interleaved runs, median).
3. Read `EXPLAIN ANALYZE` and name the operator and row count that dominate.
4. State, with a number, where DuckDB is the wrong engine.
5. Recommend what moves to the analytical copy and how that copy stays fresh.

## Files
| Script | Round | What it does |
|---|---|---|
| [prepare.py](prepare.py) | 1 | Stretches Module 5's `report_jobpart` to ten quarters in `history.db` (2,000,000 rows) and writes the 200k CSV |
| [to_parquet.py](to_parquet.py) | 2 | DuckDB expands the CSV to `report_history.parquet`, then checks the sums on both sides |
| [race.py](race.py) | 3 | The module's race: two queries, two engines, interleaved, median of 5 |
| [plan.py](plan.py) | 4 | DuckDB `EXPLAIN ANALYZE` |
| [boundary.py](boundary.py) | 5 | 1,000 single-row inserts and lookups, plus the `executemany` variant |
| [refresh.py](refresh.py) | Homework | Rebuilds the Parquet from `history.db`; `--check` compares rows and checksum and exits 1 on a mismatch |
| [run_module6a.py](run_module6a.py) | All | Runs everything plus the extra checks, and saves [results.txt](results.txt) |

The database, the CSV and the Parquet files are **not** committed; the scripts rebuild them. Notes and the memo: [duckdb-notes.md](duckdb-notes.md). Reflection: [Reflection 6a](../Reflections/ref06a.md).

## Rounds 1 and 2: build and convert
| | Value |
|---|---|
| Rows in `history.db` | 2,000,000 (= 10 quarters × 200,000) |
| Rows in the Parquet | 2,000,000 |
| `SUM(part_price)` SQLite / Parquet | 21,000,000.0 / 21,000,000.0, **identical** |
| Size: `history.db` | 112.65 MB |
| Size: Parquet (snappy, default) | 2.40 MB, **about 47× smaller** |
| Size: Parquet (zstd) | 1.39 MB |

## Round 3: the race
**First, a bug in the race as the module wrote it.** The monthly query uses `strftime(done_on, '%Y-%m')`. That is DuckDB's argument order; SQLite's is `strftime('%Y-%m', done_on)`. In SQLite the query returned **50 rows with `NULL` as the month**, while DuckDB returned **1,500** correct rows. The race was timing two different answers. With SQLite's order fixed, both engines return identical results. So checking the answer comes before timing it.

**The fair race** (both sides return the same answer; warm-up run first, then 5 interleaved runs, median and [min–max]):

| Query | SQLite | DuckDB (Parquet) | Ratio |
|---|---|---|---|
| Dashboard (since 2026-01-01) | 2,507.6 ms [2,297–2,691] | 29.5 ms [23.8–33.7] | **85×** |
| Monthly report | 2,606.7 ms [2,586–2,713] | 25.6 ms [23.8–27.5] | **102×** |
| Monthly with `date_trunc` (DuckDB) | 2,770.7 ms | 47.6 ms | 58× |
| One day, no index | 155.3 ms | 4.1 ms | 38× |
| **One day, SQLite with an index on `done_on`** | **1.9 ms** | 4.0 ms | **0.48×: SQLite wins** |

- `date_trunc` gave the same jobs and cost, but on my laptop it made DuckDB **slower** (47.6 vs 25.6 ms), the opposite of what the module predicts.
- **What makes SQLite win:** a point query on an index. The plan became `SEARCH report_history USING INDEX ix_hist_done_on (done_on=?)`, and SQLite answered in 1.9 ms against DuckDB's 4.0 ms.

## Round 4: the plans
**SQLite** (`EXPLAIN QUERY PLAN`, a prediction):
```
SCAN report_history
USE TEMP B-TREE FOR GROUP BY
```
**DuckDB** (`EXPLAIN ANALYZE`, a measurement), read bottom-up:

| Operator | Rows | Time | Note |
|---|---|---|---|
| TABLE_SCAN (READ_PARQUET) | **2,000,000** | 0.04 s | Projections: `machine_id, site, technician, part_price`: **4 of 7 columns** |
| PROJECTION | 2,000,000 | 0.00 s | |
| **HASH_GROUP_BY** | 350 | **0.12 s** | **dominates the time**: it hashes 2,000,000 input rows into 350 groups |

The scan read only the 4 columns the query needs. With `SELECT *`, the projections include `job_id`, `part_no` and `done_on` too, with the same 2,000,000 rows. SQLite has to read **whole rows** on every pass, which is most of the 85× gap. (Operator times are summed over DuckDB's threads, so they add up to more than the 0.056 s total.)

## Round 5: the boundary
1,000 single-row statements:

| | SQLite | DuckDB | DuckDB `executemany` |
|---|---|---|---|
| 1,000 inserts | **3.6 ms** | 1,085.6 ms (about 300× slower) | 744.8 ms |
| 1,000 lookups by id | **2.1 ms** | 518.4 ms (about 250× slower) | — |

**For Kortmann, DuckDB is the wrong engine when the work is one row at a time:** recording a job, reading one machine's latest reading. Each statement pays DuckDB's per-statement cost of about 1 ms, which SQLite does in microseconds. Batching with `executemany` helped only about 1.5× here, because the engine is still built for scanning millions of rows, not for answering one row.

## Homework: refresh, twice
```
rows=2000000 checksum=21000000.0 parquet_bytes=2460682 elapsed_ms=8229
check: sqlite rows=2000000 sum=21000000.0 | parquet rows=2000000 sum=21000000.0
check: OK

rows=2000000 checksum=21000000.0 parquet_bytes=2460682 elapsed_ms=8257
check: sqlite rows=2000000 sum=21000000.0 | parquet rows=2000000 sum=21000000.0
check: OK
```
Idempotent: both runs gave the same rows, checksum and even the same file size. A full rebuild takes about 8 seconds.

## Round 6: memo
See [duckdb-notes.md](duckdb-notes.md#round-6-memo-to-lea-winter-and-yasmin-kaya).
