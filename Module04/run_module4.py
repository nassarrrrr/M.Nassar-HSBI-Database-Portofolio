"""Run the whole Module 4 lab and save the evidence to Module04/results.txt.

Run from the repository root:   uv run python Module04/run_module4.py
"""
import os
import sqlite3
import statistics
import stat
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
DB = HERE / "edge.db"
OUT = HERE / "results.txt"

lines = []
def say(text=""):
    print(text)
    lines.append(str(text))

def layer(err: str) -> str:
    e = err.lower()
    if "foreign key" in e:
        return "referential integrity"
    if "unique" in e or "not null" in e or "primary key" in e:
        return "entity integrity"
    if "check" in e:
        return "domain (semantic) integrity: CHECK"
    if "cannot store" in e:
        return "domain (semantic) integrity: STRICT type"
    return "?"

def attempt(conn, label, sql, params=()):
    try:
        conn.execute(sql, params)
        say(f"  ACCEPTED  {label}")
    except sqlite3.Error as e:
        say(f"  REJECTED  {label}\n            error: {e}\n            layer: {layer(str(e))}")

def connect(path):
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

say("=" * 70)
say(f"SQLite version (Python): {sqlite3.sqlite_version}")
say("=" * 70)

# ---------------------------------------------------------------- Task A
say("\nTASK A: the acceptance test")
say("-- unconstrained table: t(sensor_id INTEGER, metric TEXT, value REAL)")
scratch = sqlite3.connect(":memory:")
scratch.execute("CREATE TABLE t(sensor_id INTEGER, metric TEXT, value REAL)")
junk = [
    (1, "temp_c", 9000), (1, "temp_c", "hot"), (2, "bogus", -500),
    ("abc", "temp_c", 20), (None, None, None), (1, "Temp_C", 20), (1, "temp_c", "20"),
]
scratch.executemany("INSERT INTO t VALUES (?,?,?)", junk)
for row in scratch.execute("SELECT sensor_id, typeof(sensor_id), metric, value, typeof(value) FROM t"):
    say(f"  stored: {row}")
say("  -> every junk row landed; nothing complained")

say("\n-- the same table with constraints, inserts one at a time")
scratch.execute("""
CREATE TABLE t2(
    reading_id INTEGER PRIMARY KEY,
    sensor_id  INTEGER NOT NULL,
    metric     TEXT    NOT NULL CHECK (metric IN ('temp_c','vib_rms','spindle_load')),
    value      REAL    CHECK (value BETWEEN -273.15 AND 5000)
) STRICT""")
for label, row in [
    ("(1,'temp_c',9000)   impossible temperature", (1, "temp_c", 9000)),
    ("(1,'temp_c','hot')  text in a REAL column", (1, "temp_c", "hot")),
    ("(2,'bogus',-500)    unknown metric", (2, "bogus", -500)),
    ("('abc','temp_c',20) text in an INTEGER column", ("abc", "temp_c", 20)),
    ("(NULL,'temp_c',20)  missing sensor", (None, "temp_c", 20)),
    ("(1,'Temp_C',20)     wrong upper/lower case", (1, "Temp_C", 20)),
    ("(1,'temp_c',NULL)   missing value: does CHECK stop NULL?", (1, "temp_c", None)),
    ("(1,'temp_c','20')   the number 20 written as text", (1, "temp_c", "20")),
    ("(1,'temp_c',4999)   plausible type, wrong value", (1, "temp_c", 4999)),
]:
    attempt(scratch, label, "INSERT INTO t2(sensor_id, metric, value) VALUES (?,?,?)", row)
for row in scratch.execute("SELECT sensor_id, metric, value, typeof(value) FROM t2"):
    say(f"  stored in t2: {row}")

# ---------------------------------------------------------------- setup
say("\n" + "=" * 70)
say("SETUP: Module04/edge.db from setup.sql")
say("=" * 70)
if DB.exists():
    os.chmod(DB, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)   # 644
    DB.unlink()
conn = connect(DB)
conn.executescript((HERE / "setup.sql").read_text())
say("  tables: " + ", ".join(r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")))

# ---------------------------------------------------------------- Task 1
say("\n" + "=" * 70)
say("TASK 1: prove the constraints work")
say("=" * 70)
attempt(conn, "valid: two sensors",
        "INSERT INTO sensor VALUES (1,'cnc-01','temp_c','degC'), (2,'cnc-01','vib_rms','mm/s')")
attempt(conn, "valid: reading 41.5",
        "INSERT INTO reading(sensor_id, ts, value, interval_s) VALUES (1,'2026-03-01 08:00:00', 41.5, 1)")
attempt(conn, "impossible temperature 9000",
        "INSERT INTO reading(sensor_id, ts, value, interval_s) VALUES (1,'2026-03-01 08:00:01', 9000, 1)")
attempt(conn, "text 'hot' into a REAL column",
        "INSERT INTO reading(sensor_id, ts, value, interval_s) VALUES (1,'2026-03-01 08:00:02', 'hot', 1)")
attempt(conn, "sensor 99 does not exist",
        "INSERT INTO reading(sensor_id, ts, value, interval_s) VALUES (99,'2026-03-01 08:00:03', 40, 1)")
attempt(conn, "duplicate sensor for cnc-01 + temp_c",
        "INSERT INTO sensor VALUES (3,'cnc-01','temp_c','degC')")
attempt(conn, "interval_s = 0",
        "INSERT INTO reading(sensor_id, ts, value, interval_s) VALUES (1,'2026-03-01 08:00:04', 40, 0)")
conn.commit()
row = conn.execute("SELECT reading_id, value, interval_s, energy_j FROM reading").fetchone()
say(f"\n  generated column: reading {row[0]}: value {row[1]} x interval_s {row[2]} = energy_j {row[3]}")

say("\n-- why PRAGMA foreign_keys matters: the same orphan insert on a connection WITHOUT it")
loose = sqlite3.connect(DB)            # foreign_keys is OFF by default
try:
    loose.execute("INSERT INTO reading(sensor_id, ts, value, interval_s) VALUES (99,'2026-03-01 08:00:03', 40, 1)")
    say("  ACCEPTED: the orphan reading for sensor 99 got in (rolled back again)")
except sqlite3.Error as e:
    say(f"  REJECTED: {e}")
loose.rollback()
loose.close()

# ---------------------------------------------------------------- Task 2
say("\n" + "=" * 70)
say("TASK 2: idempotent ingestion with UPSERT")
say("=" * 70)
conn.execute("CREATE UNIQUE INDEX ux_reading_sensor_ts ON reading(sensor_id, ts)")
conn.execute("""
INSERT INTO reading(sensor_id, ts, value, interval_s)
VALUES (1,'2026-03-01 08:00:00', 41.7, 1)
ON CONFLICT(sensor_id, ts) DO UPDATE SET value = excluded.value""")
conn.commit()
for r in conn.execute("SELECT sensor_id, ts, value FROM reading WHERE sensor_id = 1"):
    say(f"  {r}")
say("  -> still exactly one row for that key; the value was corrected 41.5 -> 41.7")
conn.close()

say("\n-- ingest.py run twice on the same CSV (10 rows)")
for run in (1, 2):
    out = subprocess.run([sys.executable, str(HERE / "ingest.py")], capture_output=True, text=True)
    say(f"  run {run}: {out.stdout.strip()} {out.stderr.strip()}")
conn = connect(DB)
n = conn.execute("SELECT COUNT(*) FROM reading").fetchone()[0]
d = conn.execute("SELECT COUNT(*) FROM (SELECT sensor_id, ts FROM reading GROUP BY 1,2 HAVING COUNT(*)>1)").fetchone()[0]
say(f"  -> {n} rows in total (1 from Task 1 + 10 from the CSV), duplicate keys: {d}")

# ---------------------------------------------------------------- Task 3
say("\n" + "=" * 70)
say("TASK 3: triggers for alarms and audit")
say("=" * 70)
conn.executescript((HERE / "triggers.sql").read_text())
conn.execute("INSERT INTO reading(sensor_id, ts, value, interval_s) VALUES (2,'2026-03-01 09:00:00', 2.7, 1)")
conn.execute("UPDATE reading SET value = 1.4 WHERE sensor_id = 2")
conn.commit()
say("-- alarm table (after inserting vibration 2.7)")
for r in conn.execute("SELECT * FROM alarm"):
    say(f"  {r}")
say("-- audit table (after updating the value to 1.4)")
for r in conn.execute("SELECT * FROM audit"):
    say(f"  {r}")

say("\n-- trigger cost: insert 10,000 vibration readings, median of 3 runs")
def ingest_cost(with_trigger: bool) -> float:
    times = []
    for _ in range(3):
        m = connect(":memory:")
        m.executescript((HERE / "setup.sql").read_text())
        m.execute("INSERT INTO sensor VALUES (2,'cnc-01','vib_rms','mm/s')")
        m.executescript((HERE / "triggers.sql").read_text())
        if not with_trigger:
            m.execute("DROP TRIGGER trg_vib_alarm")
        rows = [(2, f"2026-03-02 {i // 3600:02d}:{i // 60 % 60:02d}:{i % 60:02d}",
                 1.0 + (i % 15) / 10, 1) for i in range(10_000)]          # 4 of every 15 rows are above 2.0
        t0 = time.perf_counter()
        with m:
            m.executemany("INSERT INTO reading(sensor_id, ts, value, interval_s) VALUES (?,?,?,?)", rows)
        times.append((time.perf_counter() - t0) * 1000)
        alarms = m.execute("SELECT COUNT(*) FROM alarm").fetchone()[0]
        m.close()
    say(f"  {'with' if with_trigger else 'without':7s} alarm trigger: median {statistics.median(times):.1f} ms "
        f"(runs: {', '.join(f'{t:.1f}' for t in times)}), alarms raised: {alarms}")
    return statistics.median(times)
without = ingest_cost(False)
with_t = ingest_cost(True)
say(f"  -> the trigger adds about {with_t - without:.1f} ms per 10,000 rows ({with_t / without:.2f}x)")

# ---------------------------------------------------------------- Task 4
say("\n" + "=" * 70)
say("TASK 4: access control without a server")
say("=" * 70)
conn.execute("""CREATE VIEW machine_health AS
  SELECT s.machine_id, s.metric, MAX(r.value) AS peak, COUNT(*) AS n
  FROM sensor s JOIN reading r USING(sensor_id) GROUP BY s.machine_id, s.metric""")
conn.commit()
say("-- the machine_health view (a safe subset for report readers)")
for r in conn.execute("SELECT * FROM machine_health"):
    say(f"  {r}")
conn.close()

os.chmod(DB, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)          # chmod 444
say(f"\n-- chmod 444 Module04/edge.db  ->  {stat.filemode(DB.stat().st_mode)}")
uri = f"file:{DB}?mode=ro"
ro = sqlite3.connect(uri, uri=True)
say(f"  mode=ro  SELECT COUNT(*) FROM reading  ->  {ro.execute('SELECT COUNT(*) FROM reading').fetchone()[0]}")
try:
    ro.execute("DELETE FROM reading")
    say("  mode=ro  DELETE FROM reading  ->  ACCEPTED (unexpected!)")
except sqlite3.Error as e:
    say(f"  mode=ro  DELETE FROM reading  ->  REJECTED: {e}")
ro.close()
rw = sqlite3.connect(DB)
try:
    rw.execute("DELETE FROM reading")
    rw.rollback()
    say("  normal connection on the 444 file, DELETE  ->  ACCEPTED (file permissions do not stop an admin/root user)")
except sqlite3.Error as e:
    say(f"  normal connection on the 444 file, DELETE  ->  REJECTED: {e}")
rw.close()
os.chmod(DB, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)  # chmod 644
say(f"-- chmod 644 Module04/edge.db  ->  {stat.filemode(DB.stat().st_mode)} (write access restored)")

OUT.write_text("\n".join(lines) + "\n")
print(f"\nSaved everything to {OUT}")
