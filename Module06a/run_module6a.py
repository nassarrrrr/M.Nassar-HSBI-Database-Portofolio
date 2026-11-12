"""Run the whole Module 6a lab and save the evidence to Module06a/results.txt.

Run from the repository root:   uv run python Module06a/run_module6a.py
Needs Module05/normalize.db (run Module05/run_module5.py first if it is missing).
"""
import sqlite3
import statistics
import subprocess
import sys
import time
from pathlib import Path

import duckdb

HERE = Path(__file__).parent
OUT = HERE / "results.txt"
lines = []

def say(text=""):
    print(text)
    lines.append(str(text))

def run(script, *args):
    say(f"\n$ uv run python Module06a/{script} {' '.join(args)}".rstrip())
    p = subprocess.run([sys.executable, str(HERE / script), *args], capture_output=True, text=True)
    say(p.stdout.rstrip())
    if p.stderr.strip():
        say(p.stderr.rstrip())
    say(f"(exit status {p.returncode})")
    return p.returncode

def timed(fn):
    t0 = time.perf_counter(); fn(); return (time.perf_counter() - t0) * 1000

def race(pairs, runs=5):
    """pairs: {name: (sqlite_fn, duckdb_fn)} -> warm, interleave, median."""
    for name, (fs, fd) in pairs.items():
        fs(); fd()
        st, dt = [], []
        for _ in range(runs):
            st.append(timed(fs)); dt.append(timed(fd))
        s, d = statistics.median(st), statistics.median(dt)
        say(f"  {name:28s} sqlite {s:8.1f} ms [{min(st):.1f}-{max(st):.1f}]   "
            f"duckdb {d:7.1f} ms [{min(dt):.1f}-{max(dt):.1f}]   {s / d:7.2f}x")

say("=" * 72)
say(f"SQLite {sqlite3.sqlite_version} | DuckDB {duckdb.__version__} | Python {sys.version.split()[0]}")
say("=" * 72)

say("\nROUND 1: build the history")
if run("prepare.py") != 0:
    OUT.write_text("\n".join(lines) + "\n"); raise SystemExit(1)

say("\nROUND 2: convert to Parquet (and check both sides agree)")
run("to_parquet.py")

say("\nROUND 3: the race, exactly as the module wrote it")
run("race.py")

sq = sqlite3.connect(HERE / "history.db")
duck = duckdb.connect()
pq = str(HERE / "report_history.parquet")
src_s, src_d = "report_history", f"read_parquet('{pq}')"

say("\n-- same answer? (checked before trusting any timing)")
DASH = """SELECT machine_id, site, technician, SUM(part_price) AS cost
FROM {src} WHERE done_on >= '2026-01-01' GROUP BY machine_id, site, technician"""
MONTHLY_AS_WRITTEN = """SELECT strftime(done_on, '%Y-%m') AS month, machine_id,
       COUNT(*) AS jobs, SUM(part_price) AS cost
FROM {src} GROUP BY month, machine_id ORDER BY month, machine_id"""
MONTHLY_SQLITE = MONTHLY_AS_WRITTEN.replace("strftime(done_on, '%Y-%m')", "strftime('%Y-%m', done_on)")
MONTHLY_TRUNC = MONTHLY_AS_WRITTEN.replace("strftime(done_on, '%Y-%m')", "date_trunc('month', done_on)")

a = sorted(sq.execute(DASH.format(src=src_s)).fetchall())
b = sorted(duck.execute(DASH.format(src=src_d)).fetchall())
say(f"  dashboard: sqlite {len(a)} rows, duckdb {len(b)} rows, identical: {a == b}")
ms = sq.execute(MONTHLY_AS_WRITTEN.format(src=src_s)).fetchall()
md = duck.execute(MONTHLY_AS_WRITTEN.format(src=src_d)).fetchall()
say(f"  monthly as written: sqlite {len(ms)} rows, first {ms[0]} | duckdb {len(md)} rows, first {md[0]}")
say("  -> NOT the same answer. SQLite's strftime takes (format, date); DuckDB's takes (date, format).")
say("     In SQLite, strftime(done_on, '%Y-%m') returns NULL, so every month collapses into one NULL group.")
mf = sq.execute(MONTHLY_SQLITE.format(src=src_s)).fetchall()
say(f"  monthly fixed for SQLite, strftime('%Y-%m', done_on): {len(mf)} rows, identical to DuckDB: "
    f"{[tuple(map(str, r)) for r in mf] == [tuple(map(str, r)) for r in md]}")

mt = duck.execute(MONTHLY_TRUNC.format(src=src_d)).fetchall()
say(f"  duckdb with date_trunc: {len(mt)} rows, first {mt[0]}; same jobs and cost as strftime: "
    f"{[r[1:] for r in mt] == [r[1:] for r in md]} (the month is a DATE now, not the text 'YYYY-MM')")

say("\n-- the fair race (same answer on both sides), median of 5, interleaved")
race({
    "dashboard": (lambda: sq.execute(DASH.format(src=src_s)).fetchall(),
                  lambda: duck.execute(DASH.format(src=src_d)).fetchall()),
    "monthly (correct per engine)": (lambda: sq.execute(MONTHLY_SQLITE.format(src=src_s)).fetchall(),
                                     lambda: duck.execute(MONTHLY_AS_WRITTEN.format(src=src_d)).fetchall()),
    "monthly, duckdb date_trunc": (lambda: sq.execute(MONTHLY_SQLITE.format(src=src_s)).fetchall(),
                                   lambda: duck.execute(MONTHLY_TRUNC.format(src=src_d)).fetchall()),
})

say("\n-- what would make SQLite win? a point query on an index")
POINT = "SELECT COUNT(*), SUM(part_price) FROM {src} WHERE done_on = '2026-02-14'"
say(f"  answer: sqlite {sq.execute(POINT.format(src=src_s)).fetchone()} | duckdb {duck.execute(POINT.format(src=src_d)).fetchone()}")
race({"one day, no index": (lambda: sq.execute(POINT.format(src=src_s)).fetchall(),
                            lambda: duck.execute(POINT.format(src=src_d)).fetchall())})
sq.execute("CREATE INDEX IF NOT EXISTS ix_hist_done_on ON report_history(done_on)")
race({"one day, sqlite with index": (lambda: sq.execute(POINT.format(src=src_s)).fetchall(),
                                     lambda: duck.execute(POINT.format(src=src_d)).fetchall())})
say("  sqlite plan: " + " | ".join(r[3] for r in sq.execute("EXPLAIN QUERY PLAN " + POINT.format(src=src_s))))
sq.execute("DROP INDEX ix_hist_done_on")
sq.commit()
sq.execute("VACUUM")    # give the dropped index's pages back, so the file size stays comparable

say("\nROUND 4: the plans")
say("-- SQLite (a prediction, no timings)")
for r in sq.execute("EXPLAIN QUERY PLAN " + DASH.format(src=src_s)):
    say(f"    {r[3]}")
say("-- DuckDB EXPLAIN ANALYZE (a measurement: it runs the query)")
run("plan.py")
say("-- SELECT * instead: which columns does the scan read now?")
star = duck.execute(f"EXPLAIN ANALYZE SELECT * FROM read_parquet('{pq}')").fetchall()[0][1]
proj = [l for l in star.splitlines() if any(c in l for c in ("job_id", "part_no", "done_on", "Projections"))]
say("\n".join(proj))

say("\nROUND 5: the boundary (1,000 single-row statements)")
run("boundary.py")

say("\nHOMEWORK (core): zstd compression")
zstd = HERE / "report_zstd.parquet"
duck.execute(f"COPY (SELECT * FROM read_parquet('{pq}')) TO '{zstd}' (FORMAT parquet, COMPRESSION zstd)")
Z = f"read_parquet('{zstd}')"
race({"dashboard snappy vs zstd": (lambda: duck.execute(DASH.format(src=src_d)).fetchall(),
                                   lambda: duck.execute(DASH.format(src=Z)).fetchall())})
say("  (in this line, the 'sqlite' column is the snappy file and the 'duckdb' column is the zstd file)")
say(f"  sizes: snappy {Path(pq).stat().st_size / 1e6:.2f} MB, zstd {zstd.stat().st_size / 1e6:.2f} MB, "
    f"history.db {(HERE / 'history.db').stat().st_size / 1e6:.2f} MB")

say("\nHOMEWORK (intense track): refresh.py, run twice with --check")
run("refresh.py", "--check")
run("refresh.py", "--check")

OUT.write_text("\n".join(lines) + "\n")
print(f"\nSaved everything to {OUT}")
