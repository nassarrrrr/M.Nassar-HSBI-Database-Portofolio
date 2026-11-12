# Module06a/plan.py — run with:  uv run python Module06a/plan.py
"""The DuckDB physical plan: rows and time per operator (this runs the query)."""
import duckdb
from pathlib import Path

here = Path(__file__).parent
pq = here / "report_history.parquet"

con = duckdb.connect()
plan = con.execute(f"""
    EXPLAIN ANALYZE
    SELECT machine_id, site, technician, SUM(part_price) AS cost
    FROM read_parquet('{pq}')
    GROUP BY machine_id, site, technician
""").fetchall()[0][1]
print(plan)
