"""Run Module 6b's benches 1 and 2 (plus extra checks) and save Module06b/results.txt.

Run from the repository root:   uv run python Module06b/run_module6b.py
Bench 3 (the PostgreSQL server) happens in class and is not part of this script.
"""
import dbm
import shelve
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "results.txt"
lines = []

def say(text=""):
    print(text)
    lines.append(str(text))

def run(script):
    say(f"\n$ uv run python Module06b/{script}")
    p = subprocess.run([sys.executable, str(HERE / script)], capture_output=True, text=True)
    say(p.stdout.rstrip())
    if p.stderr.strip():
        say(p.stderr.rstrip())

say("=" * 72)
say(f"SQLite {sqlite3.sqlite_version} | Python {sys.version.split()[0]}")
say("=" * 72)

# ---------------------------------------------------------------- Bench 1
say("\nBENCH 1: metadata that will not sit still (JSON in SQLite)")
run("json_bench.py")

con = sqlite3.connect(HERE / "polyglot.db")
say("\n-- extra: CHECK (json_valid(meta)) rejects text that is not JSON")
try:
    con.execute("INSERT INTO device(name, meta) VALUES ('bad-01', '{vendor: Siemens')")
    say("  ACCEPTED (unexpected)")
except sqlite3.Error as e:
    say(f"  REJECTED: {e}")

say("\n-- extra: a vendor adds a brand-new field, with no migration")
con.execute("""INSERT INTO device(name, meta) VALUES
  ('cnc-04', '{"vendor":"Siemens","firmware":"4.3","spindle_rpm_max":12000}')""")
for r in con.execute("SELECT name, meta ->> '$.spindle_rpm_max' FROM device"):
    say(f"  {r}")
say("  -> the new key is queryable at once; older devices just return NULL")

say("\n-- extra: which spellings of the same filter use ix_device_vendor?")
for label, where in [
    ("json_extract(meta, '$.vendor')", "json_extract(meta, '$.vendor') = 'Fanuc'"),
    ("meta ->> '$.vendor'", "meta ->> '$.vendor' = 'Fanuc'"),
    ("meta ->> 'vendor'", "meta ->> 'vendor' = 'Fanuc'"),
]:
    p = " | ".join(r[3] for r in con.execute(f"EXPLAIN QUERY PLAN SELECT name FROM device WHERE {where}"))
    n = con.execute(f"SELECT COUNT(*) FROM device WHERE {where}").fetchone()[0]
    say(f"  {label:32s} -> {n} row(s), plan: {p}")
con.execute("CREATE INDEX ix_device_vendor_arrow ON device(meta ->> '$.vendor')")
p = " | ".join(r[3] for r in con.execute(
    "EXPLAIN QUERY PLAN SELECT name FROM device WHERE meta ->> '$.vendor' = 'Fanuc'"))
say(f"  after indexing the ->> expression itself      -> plan: {p}")
con.commit()
con.close()

# ---------------------------------------------------------------- Bench 2
say("\nBENCH 2: session state (key-value vs SQLite)")
for f in HERE.glob("sessions*"):
    f.unlink()
run("kv_compare.py")
backend = dbm.whichdb(str(HERE / "sessions"))
say(f"\n-- extra: which backend did shelve use on this machine? dbm.whichdb -> {backend!r}")
if backend == "dbm.sqlite3":
    say("  -> on Python 3.13+ the default dbm backend IS SQLite: shelve stores its keys in a")
    say("     SQLite table and commits every single assignment, which is why its writes are slow.")

say("\n-- extra: a question across sessions: how many sessions per city filter?")
sq = sqlite3.connect(HERE / "sessions.db")
t0 = time.perf_counter()
rows = sq.execute("""SELECT substr(v, instr(v, 'city:')) AS filter, COUNT(*) AS sessions,
                            COUNT(DISTINCT substr(v, 1, instr(v, ':') - 1)) AS users
                     FROM session GROUP BY filter ORDER BY filter""").fetchall()
t_sql = (time.perf_counter() - t0) * 1000
for r in rows:
    say(f"  {r}")
say(f"  SQLite: one GROUP BY query, {t_sql:.1f} ms")
t0 = time.perf_counter()
counts = {}
with shelve.open(str(HERE / "sessions"), flag="r") as db:
    for k in db.keys():                         # shelve can only walk every key in Python
        f = db[k].split(":", 1)[1]
        counts[f] = counts.get(f, 0) + 1
t_py = (time.perf_counter() - t0) * 1000
say(f"  shelve: no query language; a Python loop over all keys gives {dict(sorted(counts.items()))} in {t_py:.1f} ms")

OUT.write_text("\n".join(lines) + "\n")
print(f"\nSaved everything to {OUT}")
