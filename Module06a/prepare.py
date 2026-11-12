# Module06a/prepare.py — run with:  uv run python Module06a/prepare.py
"""Stretch Module 5's report table to ten quarters (2,000,000 rows)."""
import csv
import sqlite3
from pathlib import Path

here = Path(__file__).parent
src = here.parent / "Module05" / "normalize.db"
db = here / "history.db"
csv_path = here / "report_jobpart.csv"
QUARTERS = 10

if not src.exists():
    raise SystemExit("Module05/normalize.db is missing — rebuild it with the Module 5 Setup block first.")

db.unlink(missing_ok=True)
conn = sqlite3.connect(db)
conn.execute("ATTACH DATABASE ? AS m5", (str(src),))
conn.execute("""CREATE TABLE report_history(
    job_id INTEGER, machine_id TEXT, site TEXT, technician TEXT,
    part_no TEXT, part_price REAL, done_on TEXT)""")
conn.execute(f"""
    INSERT INTO report_history
    SELECT r.job_id + k * 1000000, r.machine_id, r.site, r.technician,
           r.part_no, r.part_price,
           date(r.done_on, '+' || (k * 91) || ' days')
    FROM m5.report_jobpart r, (WITH RECURSIVE n(k) AS (
         SELECT 0 UNION ALL SELECT k + 1 FROM n WHERE k < {QUARTERS - 1})
         SELECT k FROM n)""")
conn.commit()

with csv_path.open("w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["job_id", "machine_id", "site", "technician",
                     "part_no", "part_price", "done_on"])
    writer.writerows(conn.execute("SELECT * FROM m5.report_jobpart"))

print("history rows:", conn.execute("SELECT COUNT(*) FROM report_history").fetchone()[0])
print("csv bytes   :", csv_path.stat().st_size)
