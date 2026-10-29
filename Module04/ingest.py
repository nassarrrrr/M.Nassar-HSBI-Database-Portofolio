"""Replay-safe ingestion: load a CSV of readings with UPSERT.

Run from the repo root:  uv run python Module04/ingest.py [csv] [db]
Running it twice on the same file must NOT create duplicate rows.
"""
import csv
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).parent
csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "readings.csv"
db_path = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "edge.db"

UPSERT = """
INSERT INTO reading(sensor_id, ts, value, interval_s)
VALUES (?, ?, ?, ?)
ON CONFLICT(sensor_id, ts) DO UPDATE SET value = excluded.value
"""

conn = sqlite3.connect(db_path)
conn.execute("PRAGMA foreign_keys = ON")
# (sensor_id, ts) is the natural key of a reading, so a replayed row collides
conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_reading_sensor_ts ON reading(sensor_id, ts)")

with csv_path.open(newline="") as f:
    rows = [(int(r["sensor_id"]), r["ts"], float(r["value"]), int(r["interval_s"]))
            for r in csv.DictReader(f)]

with conn:                                   # one transaction for the whole batch
    conn.executemany(UPSERT, rows)

total = conn.execute("SELECT COUNT(*) FROM reading").fetchone()[0]
print(f"ingested {len(rows)} rows from {csv_path.name}; reading table now has {total} rows")
conn.close()
