"""Load Module01/telemetry.csv into Module01/telemetry.db (no sqlite3 shell needed)."""
import csv, sqlite3
from pathlib import Path

here = Path(__file__).parent
csv_path = here / "telemetry.csv"
db_path = here / "telemetry.db"

conn = sqlite3.connect(db_path)
conn.executescript("""
    DROP TABLE IF EXISTS readings;
    CREATE TABLE readings(
        ts           TEXT    NOT NULL,
        machine      TEXT    NOT NULL,
        temp_c       REAL    NOT NULL,
        vib_rms      REAL    NOT NULL,
        spindle_load REAL    NOT NULL
    );
""")
with csv_path.open(newline="") as f:
    rows = csv.reader(f)
    next(rows)                                   # skip the header
    conn.executemany("INSERT INTO readings VALUES (?, ?, ?, ?, ?)", rows)
conn.commit()
n = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
print(f"loaded {n} rows into {db_path}")
conn.close()
