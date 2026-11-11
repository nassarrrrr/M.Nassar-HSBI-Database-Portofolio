"""Run the whole Module 5 lab (Rounds 2-5 and the DuckDB stretcher) and save the
evidence to Module05/results.txt.

Run from the repository root:   uv run python Module05/run_module5.py
"""
import sqlite3
import statistics
import time
from pathlib import Path

HERE = Path(__file__).parent
DB = HERE / "normalize.db"
OUT = HERE / "results.txt"

lines = []
def say(text=""):
    print(text)
    lines.append(str(text))

def plan(conn, sql):
    return "\n".join("    " + r[3] for r in conn.execute("EXPLAIN QUERY PLAN " + sql))

def timed(conn, sql):
    t0 = time.perf_counter()
    rows = conn.execute(sql).fetchall()
    return (time.perf_counter() - t0) * 1000, rows

def race(conn, queries, runs=3):
    """Warm every query once (untimed), then alternate them `runs` times; return medians."""
    for sql in queries.values():
        conn.execute(sql).fetchall()
    times = {name: [] for name in queries}
    for _ in range(runs):
        for name, sql in queries.items():
            times[name].append(timed(conn, sql)[0])
    return {name: (statistics.median(t), t) for name, t in times.items()}

def fmt(med_runs):
    med, runs = med_runs
    return f"median {med:.1f} ms (runs: {', '.join(f'{t:.1f}' for t in runs)})"

say("=" * 70)
say(f"SQLite version (Python): {sqlite3.sqlite_version}")
say("=" * 70)

# ---------------------------------------------------------------- Round 2
say("\nROUND 2: break it (the five-row flat5 table)")
FLAT5 = """
CREATE TABLE flat5(job_id INTEGER, machine_id TEXT, site TEXT,
                   technician TEXT, part_no TEXT, part_price REAL);
INSERT INTO flat5 VALUES
  (1,'cnc-01','Gütersloh','tech-0','P-0001',6.00),
  (1,'cnc-01','Gütersloh','tech-0','P-0002',7.00),
  (2,'cnc-02','Gütersloh','tech-1','P-0001',6.00),
  (2,'cnc-02','Gütersloh','tech-1','P-0003',8.50),
  (3,'cnc-01','Gütersloh','tech-0','P-0003',8.50);
"""
def fresh5():
    c = sqlite3.connect(":memory:")
    c.executescript(FLAT5)
    return c

c = fresh5()
cur = c.execute("UPDATE flat5 SET site = 'Bielefeld' WHERE machine_id = 'cnc-01'")
say(f"-- update anomaly: UPDATE flat5 SET site='Bielefeld' WHERE machine_id='cnc-01'")
say(f"   rows touched: {cur.rowcount} (one fact, stored {cur.rowcount} times)")
c = fresh5()
cur = c.execute("UPDATE flat5 SET site = 'Bielefeld' WHERE machine_id = 'cnc-01' AND job_id = 1")
say(f"   a second session that only edits job 1 (WHERE ... AND job_id = 1) touches {cur.rowcount} rows, and then:")
for r in c.execute("SELECT DISTINCT machine_id, site FROM flat5 WHERE machine_id = 'cnc-01'"):
    say(f"     {r}")
say("   -> cnc-01 is now in two cities at once: the copies disagree")

c = fresh5()
c.execute("INSERT INTO flat5(part_no, part_price) VALUES ('P-0004', 9.00)")
say("\n-- insert anomaly: INSERT INTO flat5(part_no, part_price) VALUES ('P-0004', 9.00)")
for r in c.execute("SELECT * FROM flat5 WHERE part_no = 'P-0004'"):
    say(f"   stored: {r}")
say("   -> the only way to record a new part is a 'job' row with no job, machine or technician")

c = fresh5()
cur = c.execute("DELETE FROM flat5 WHERE job_id = 1")
say(f"\n-- delete anomaly: DELETE FROM flat5 WHERE job_id = 1   ({cur.rowcount} rows)")
left = c.execute("SELECT part_price FROM flat5 WHERE part_no = 'P-0002'").fetchall()
say(f"   price of P-0002 afterwards: {left}")
say("   -> job 1 was the only job that used P-0002, so the fact 'P-0002 costs 7.00' vanished with it")

# ---------------------------------------------------------------- Round 3
say("\n" + "=" * 70)
say("ROUND 3: build it (Module05/normalize.db)")
say("=" * 70)
if DB.exists():
    DB.unlink()
conn = sqlite3.connect(DB, cached_statements=0)   # no statement cache: plans reflect DROP INDEX
t0 = time.perf_counter()
conn.executescript((HERE / "setup.sql").read_text())
say(f"flat_jobpart built in {(time.perf_counter() - t0):.1f} s")
conn.executescript((HERE / "normalize.sql").read_text())
conn.commit()
for t in ("flat_jobpart", "machine", "part", "job", "job_part"):
    say(f"  {t:13s} rows: {conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")
flat_n, norm_n = conn.execute(
    "SELECT (SELECT COUNT(*) FROM flat_jobpart), (SELECT COUNT(*) FROM job_part)").fetchone()
say(f"  integrity check: flat_rows = {flat_n}, normalized_rows = {norm_n}  ->  {'MATCH' if flat_n == norm_n else 'MISMATCH'}")
used = conn.execute("SELECT GROUP_CONCAT(part_no, ', ') FROM part").fetchone()[0]
say(f"  part numbers used: {used}")
say("  -> only 10 parts: k runs 1..10, so (k % 40) + 1 gives P-0002 .. P-0011 and never reaches 40")
reb = conn.execute("""SELECT COUNT(*) FROM flat_jobpart f JOIN job j USING(job_id)
                      JOIN machine m ON m.machine_id = j.machine_id
                      JOIN part p USING(part_no) JOIN job_part jp USING(job_id, part_no)""").fetchone()[0]
say(f"  joining the 3NF tables back together gives {reb} rows (lossless)")

say("\n-- the same decomposition with PRAGMA foreign_keys = ON (in-memory copy)")
fk = sqlite3.connect(":memory:")
conn.backup(fk)
fk.execute("PRAGMA foreign_keys = ON")
try:
    fk.executescript((HERE / "normalize.sql").read_text())
    say(f"  loaded fine: job_part rows = {fk.execute('SELECT COUNT(*) FROM job_part').fetchone()[0]}, "
        f"foreign_key_check problems = {len(fk.execute('PRAGMA foreign_key_check').fetchall())}")
except sqlite3.Error as e:
    say(f"  FAILED: {e}")
fk.close()

# ---------------------------------------------------------------- Round 4
say("\n" + "=" * 70)
say("ROUND 4: race it (normalized A vs denormalized B)")
say("=" * 70)
conn.executescript((HERE / "report.sql").read_text())
conn.commit()
say(f"report_jobpart rows: {conn.execute('SELECT COUNT(*) FROM report_jobpart').fetchone()[0]}")
say(f"one example row: {conn.execute('SELECT * FROM report_jobpart LIMIT 1').fetchone()}")

A = """SELECT m.machine_id, m.site, j.technician, SUM(p.part_price) AS cost
FROM job j
JOIN machine m   ON m.machine_id = j.machine_id
JOIN job_part jp ON jp.job_id = j.job_id
JOIN part p      ON p.part_no = jp.part_no
WHERE j.done_on >= date('2026-03-01')
GROUP BY m.machine_id, j.technician"""
B = """SELECT machine_id, site, technician, SUM(part_price) AS cost
FROM report_jobpart
WHERE done_on >= date('2026-03-01')
GROUP BY machine_id, technician"""

ra = sorted(conn.execute(A).fetchall())
rb = sorted(conn.execute(B).fetchall())
say(f"same answer? A returns {len(ra)} rows, B returns {len(rb)} rows, identical: {ra == rb}, "
    f"total cost {sum(r[3] for r in ra):,.1f}")
say("\n-- plan A (normalized)")
say(plan(conn, A))
say("-- plan B (denormalized, with ix_report_machine)")
say(plan(conn, B))
r = race(conn, {"A": A, "B": B})
say(f"\nA normalized   : {fmt(r['A'])}")
say(f"B denormalized : {fmt(r['B'])}")
dash = {"A": r["A"][0], "B": r["B"][0]}

say("\n-- optional try: make the join hurt (two more dimensions, in-memory copy)")
wide = sqlite3.connect(":memory:")
conn.backup(wide)
wide.executescript("""
CREATE TABLE vendor(part_no TEXT PRIMARY KEY, vendor TEXT NOT NULL, country TEXT NOT NULL);
INSERT INTO vendor
SELECT part_no, 'vendor-' || (rowid % 12),
       CASE rowid % 3 WHEN 0 THEN 'DE' WHEN 1 THEN 'CN' ELSE 'US' END
FROM part;
CREATE TABLE site_dim(site TEXT PRIMARY KEY, region TEXT NOT NULL, manager TEXT NOT NULL);
INSERT INTO site_dim
SELECT site, 'region-' || (row_number() OVER () % 5), 'mgr-' || row_number() OVER ()
FROM (SELECT DISTINCT site FROM machine);
DROP TABLE IF EXISTS report_jobpart;
CREATE TABLE report_jobpart AS
SELECT j.job_id, m.machine_id, m.site, sd.region, j.technician, jp.part_no,
       p.part_price, v.vendor, j.done_on
FROM job j
JOIN machine m   ON m.machine_id = j.machine_id
JOIN site_dim sd ON sd.site = m.site
JOIN job_part jp ON jp.job_id = j.job_id
JOIN part p      ON p.part_no = jp.part_no
JOIN vendor v    ON v.part_no = p.part_no;
""")
A6 = """SELECT m.machine_id, m.site, sd.region, j.technician, v.vendor, SUM(p.part_price) AS cost
FROM job j
JOIN machine m   ON m.machine_id = j.machine_id
JOIN site_dim sd ON sd.site = m.site
JOIN job_part jp ON jp.job_id = j.job_id
JOIN part p      ON p.part_no = jp.part_no
JOIN vendor v    ON v.part_no = p.part_no
WHERE j.done_on >= date('2026-03-01')
GROUP BY m.machine_id, m.site, sd.region, j.technician, v.vendor"""
B6 = """SELECT machine_id, site, region, technician, vendor, SUM(part_price) AS cost
FROM report_jobpart
WHERE done_on >= date('2026-03-01')
GROUP BY machine_id, site, region, technician, vendor"""
a6 = wide.execute(A6).fetchall()
say(f"  check: {len(a6)} rows, total {sum(x[5] for x in a6):,.1f} (module expects 3,500 rows and 722,610.0)")
r6 = race(wide, {"A6": A6, "B6": B6})
say(f"  A six-way join  : {fmt(r6['A6'])}")
say(f"  B one wide table: {fmt(r6['B6'])}")
wide.close()

# ---------------------------------------------------------------- Round 5
say("\n" + "=" * 70)
say("ROUND 5: price it (writes, storage, the index experiment)")
say("=" * 70)
say("-- dashboard B without ix_report_machine")
conn.execute("DROP INDEX ix_report_machine")
say(plan(conn, B))
r_noix = race(conn, {"B": B})
say(f"B without index: {fmt(r_noix['B'])}   (with index: median {dash['B']:.1f} ms)")
conn.execute("CREATE INDEX ix_report_machine ON report_jobpart(machine_id)")
conn.commit()

def storage():
    return {
        "norm": conn.execute("SELECT SUM(pgsize) FROM dbstat WHERE name IN ('job','job_part','part','machine')").fetchone()[0],
        "report": conn.execute("SELECT SUM(pgsize) FROM dbstat WHERE name = 'report_jobpart'").fetchone()[0],
        "report_ix": conn.execute("SELECT SUM(pgsize) FROM dbstat WHERE name = 'ix_report_machine'").fetchone()[0],
    }
try:
    st = storage()
    say(f"\n-- storage (dbstat)")
    say(f"  normalized (job + job_part + part + machine): {st['norm']:,} bytes = {st['norm'] / 1024:,.0f} KB")
    say(f"  denormalized (report_jobpart)               : {st['report']:,} bytes = {st['report'] / 1024:,.0f} KB")
    say(f"  plus ix_report_machine                      : {st['report_ix']:,} bytes = {st['report_ix'] / 1024:,.0f} KB")
except sqlite3.Error as e:
    st = None
    say(f"\n-- storage: dbstat not available in this build ({e})")

say("\n-- change one machine's site (cnc-02 -> Bielefeld)")
t0 = time.perf_counter()
cur = conn.execute("UPDATE machine SET site = 'Bielefeld' WHERE machine_id = 'cnc-02'")
t_m = (time.perf_counter() - t0) * 1000
n_m = cur.rowcount
t0 = time.perf_counter()
cur = conn.execute("UPDATE report_jobpart SET site = 'Bielefeld' WHERE machine_id = 'cnc-02'")
t_r = (time.perf_counter() - t0) * 1000
n_r = cur.rowcount
conn.commit()
say(f"  3NF    : UPDATE machine        -> {n_m} row,  {t_m:.3f} ms")
say(f"  report : UPDATE report_jobpart -> {n_r} rows, {t_r:.3f} ms")

say("\n-- summary table")
say(f"{'design':24s} {'dashboard (ms)':>15s} {'rows per site update':>21s} {'storage (KB)':>13s}")
say(f"{'normalized (3NF)':24s} {dash['A']:15.1f} {n_m:21d} {(st['norm'] / 1024 if st else 0):13,.0f}")
say(f"{'denormalized (report)':24s} {dash['B']:15.1f} {n_r:21d} {(st['report'] / 1024 if st else 0):13,.0f}")
conn.close()

# ---------------------------------------------------------------- stretcher
say("\n" + "=" * 70)
say("STRETCHER: the same dashboard in DuckDB (columnar engine)")
say("=" * 70)
try:
    import duckdb
    d = duckdb.connect()
    d.execute("""
    CREATE TABLE flat_jobpart AS
    SELECT n AS job_id,
           'cnc-' || lpad(CAST((n % 50) + 1 AS VARCHAR), 2, '0') AS machine_id,
           CASE (n % 50) WHEN 0 THEN 'Bielefeld' ELSE 'Gütersloh' END AS site,
           'tech-' || CAST(n % 7 AS VARCHAR) AS technician,
           'P-' || lpad(CAST((k % 40) + 1 AS VARCHAR), 4, '0') AS part_no,
           CAST(5 + (k % 40) AS DOUBLE) AS part_price,
           strftime(DATE '2026-01-01' + CAST(n % 90 AS INTEGER), '%Y-%m-%d') AS done_on
    FROM range(1, 20001) j(n) CROSS JOIN range(1, 11) p(k)""")
    d.execute("CREATE TABLE machine AS SELECT DISTINCT machine_id, site FROM flat_jobpart")
    d.execute("CREATE TABLE part AS SELECT DISTINCT part_no, part_price FROM flat_jobpart")
    d.execute("CREATE TABLE job AS SELECT DISTINCT job_id, machine_id, technician, done_on FROM flat_jobpart")
    d.execute("CREATE TABLE job_part AS SELECT DISTINCT job_id, part_no FROM flat_jobpart")
    d.execute("""CREATE TABLE report_jobpart AS
        SELECT j.job_id, m.machine_id, m.site, j.technician, jp.part_no, p.part_price, j.done_on
        FROM job j JOIN machine m ON m.machine_id = j.machine_id
        JOIN job_part jp ON jp.job_id = j.job_id JOIN part p ON p.part_no = jp.part_no""")
    say("note: DuckDB rejects the SQLite query as written: 'column \"site\" must appear in the GROUP BY")
    say("clause'. SQLite silently allows a bare column that is not grouped; DuckDB (and standard SQL) do not.")
    say("So for DuckDB, site is added to GROUP BY (it is the same value per machine anyway).")
    Ad = A.replace("date('2026-03-01')", "'2026-03-01'").replace(
        "GROUP BY m.machine_id, j.technician", "GROUP BY m.machine_id, m.site, j.technician")
    Bd = B.replace("date('2026-03-01')", "'2026-03-01'").replace(
        "GROUP BY machine_id, technician", "GROUP BY machine_id, site, technician")
    ad = sorted(d.execute(Ad).fetchall())
    say(f"DuckDB {duckdb.__version__}: A returns {len(ad)} rows, same answer as SQLite: {ad == ra}")
    times = {"A": [], "B": []}
    d.execute(Ad).fetchall(); d.execute(Bd).fetchall()          # warm
    for _ in range(3):
        for name, sql in (("A", Ad), ("B", Bd)):
            t0 = time.perf_counter(); d.execute(sql).fetchall()
            times[name].append((time.perf_counter() - t0) * 1000)
    say(f"  A normalized   : {fmt((statistics.median(times['A']), times['A']))}")
    say(f"  B denormalized : {fmt((statistics.median(times['B']), times['B']))}")
    say(f"  (SQLite        : A {dash['A']:.1f} ms, B {dash['B']:.1f} ms)")
except ImportError:
    say("duckdb is not installed in this environment (run: uv add duckdb)")

OUT.write_text("\n".join(lines) + "\n")
print(f"\nSaved everything to {OUT}")
