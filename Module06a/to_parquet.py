# Module06a/to_parquet.py — run with:  uv run python Module06a/to_parquet.py
"""200k CSV -> 2M-row Parquet. DuckDB does the expansion, no database server involved."""
import sqlite3
from pathlib import Path

import duckdb

here = Path(__file__).parent
csv_path = here / "report_jobpart.csv"
parquet = here / "report_history.parquet"

con = duckdb.connect()          # in-process, embedded — nothing to start
con.execute(f"""
    COPY (
      SELECT r.job_id + k * 1000000 AS job_id, r.machine_id, r.site,
             r.technician, r.part_no, r.part_price,
             CAST(r.done_on AS DATE) + CAST(k * 91 AS INTEGER) AS done_on
      FROM read_csv_auto('{csv_path}', header = true) r,
           range(0, 10) t(k)
    ) TO '{parquet}' (FORMAT parquet)
""")

print("parquet rows:", con.execute(
    f"SELECT COUNT(*) FROM read_parquet('{parquet}')").fetchone()[0])
print("parquet MB  :", round(parquet.stat().st_size / 1e6, 2))

# both sides must agree before anything is timed
pq_sum = con.execute(f"SELECT ROUND(SUM(part_price), 2) FROM read_parquet('{parquet}')").fetchone()[0]
sq = sqlite3.connect(here / "history.db")
sq_sum = sq.execute("SELECT ROUND(SUM(part_price), 2) FROM report_history").fetchone()[0]
print("sum parquet :", pq_sum)
print("sum sqlite  :", sq_sum)
print("identical   :", pq_sum == sq_sum)
print("sqlite MB   :", round((here / "history.db").stat().st_size / 1e6, 2))
