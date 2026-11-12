# Module06a/refresh.py — run with:  uv run python Module06a/refresh.py [--check]
"""Rebuild report_history.parquet from history.db, and optionally verify it.

--check  compares row count and SUM(part_price) between SQLite and the Parquet,
         prints both, and exits with status 1 on a mismatch.
Always prints one line: rows, checksum, Parquet size, elapsed milliseconds.
"""
import csv
import sqlite3
import sys
import time
from pathlib import Path

import duckdb

here = Path(__file__).parent
db = here / "history.db"
parquet = here / "report_history.parquet"
tmp_csv = here / "_refresh.csv"

t0 = time.perf_counter()
if not db.exists():
    raise SystemExit("Module06a/history.db is missing: run prepare.py first.")

# 1. export the operational table (SQLite) to a temporary CSV
sq = sqlite3.connect(db)
with tmp_csv.open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["job_id", "machine_id", "site", "technician", "part_no", "part_price", "done_on"])
    w.writerows(sq.execute("SELECT * FROM report_history"))

# 2. write the analytical copy (Parquet) in one COPY
con = duckdb.connect()
con.execute(f"""
    COPY (SELECT job_id, machine_id, site, technician, part_no, part_price,
                 CAST(done_on AS DATE) AS done_on
          FROM read_csv_auto('{tmp_csv}', header = true))
    TO '{parquet}' (FORMAT parquet)""")
tmp_csv.unlink()

pq_rows, pq_sum = con.execute(
    f"SELECT COUNT(*), ROUND(SUM(part_price), 2) FROM read_parquet('{parquet}')").fetchone()
elapsed = (time.perf_counter() - t0) * 1000
print(f"rows={pq_rows} checksum={pq_sum} parquet_bytes={parquet.stat().st_size} elapsed_ms={elapsed:.0f}")

if "--check" in sys.argv:
    sq_rows, sq_sum = sq.execute(
        "SELECT COUNT(*), ROUND(SUM(part_price), 2) FROM report_history").fetchone()
    print(f"check: sqlite rows={sq_rows} sum={sq_sum} | parquet rows={pq_rows} sum={pq_sum}")
    if (sq_rows, sq_sum) != (pq_rows, pq_sum):
        print("check: MISMATCH")
        sys.exit(1)
    print("check: OK")
