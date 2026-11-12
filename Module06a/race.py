# Module06a/race.py — run with:  uv run python Module06a/race.py
"""Same two queries, two engines, interleaved, median of RUNS runs."""
import sqlite3
import statistics
import time
from pathlib import Path

import duckdb

RUNS = 5        # odd on purpose: the median is then a real run. Try 3, 7, 9.

here = Path(__file__).parent
sq = sqlite3.connect(here / "history.db")
duck = duckdb.connect()
pq = str(here / "report_history.parquet")

DASHBOARD = """SELECT machine_id, site, technician, SUM(part_price) AS cost
FROM {src} WHERE done_on >= '2026-01-01'
GROUP BY machine_id, site, technician"""

MONTHLY = """SELECT strftime(done_on, '%Y-%m') AS month, machine_id,
       COUNT(*) AS jobs, SUM(part_price) AS cost
FROM {src} GROUP BY month, machine_id ORDER BY month, machine_id"""


def timed_ms(fn):
    t0 = time.perf_counter()
    fn()
    return (time.perf_counter() - t0) * 1000


def spread(times):
    return f"{min(times):.1f}-{max(times):.1f}"


for name, sql in (("dashboard", DASHBOARD), ("monthly", MONTHLY)):
    run_sqlite = lambda: sq.execute(sql.format(src="report_history")).fetchall()
    run_duckdb = lambda: duck.execute(sql.format(src=f"read_parquet('{pq}')")).fetchall()

    run_sqlite()          # warm-up: load the pages, discard the timing
    run_duckdb()

    sqlite_times, duckdb_times = [], []
    for _ in range(RUNS):  # interleaved: alternate the engines
        sqlite_times.append(timed_ms(run_sqlite))
        duckdb_times.append(timed_ms(run_duckdb))

    s = statistics.median(sqlite_times)
    d = statistics.median(duckdb_times)
    print(f"{name:10s} sqlite {s:7.1f} ms [{spread(sqlite_times)}]"
          f"   duckdb {d:6.1f} ms [{spread(duckdb_times)}]   {s / d:6.1f}x")
