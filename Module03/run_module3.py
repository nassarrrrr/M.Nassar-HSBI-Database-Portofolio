"""Run the whole Module 3 lab and save the evidence to Module03/results.txt.

Run from the repository root:   uv run python Module03/run_module3.py
"""
import sqlite3
import statistics
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
DB = HERE / "warehouse.db"
LEGACY = HERE.parent / "Module02" / "legacy.db"
LLM_SQL = HERE / "llm_query.sql"
OUT = HERE / "results.txt"

lines = []
def say(text=""):
    print(text)
    lines.append(str(text))

def plan(conn, sql, params=()):
    rows = conn.execute("EXPLAIN QUERY PLAN " + sql, params).fetchall()
    return "\n".join("    " + r[3] for r in rows)

def median_ms(conn, sql, params=(), runs=3, batch=1):
    """Median of `runs` timings; each timing runs the query `batch` times."""
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        for _ in range(batch):
            conn.execute(sql, params).fetchall()
        times.append((time.perf_counter() - t0) * 1000 / batch)
    return statistics.median(times), times

# ---------------------------------------------------------------- setup
say("=" * 70)
say(f"SQLite version (Python): {sqlite3.sqlite_version}")
say("=" * 70)
if DB.exists():
    DB.unlink()
conn = sqlite3.connect(DB)
conn.executescript((HERE / "setup.sql").read_text())
conn.commit()
for t in ("customer", "product", "orders", "order_line"):
    say(f"{t:11s} rows: {conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}")

# ---------------------------------------------------------------- Task A
say("\n" + "=" * 70)
say("TASK A: plan safari on Module02/legacy.db (copy in memory, original untouched)")
say("=" * 70)
if LEGACY.exists():
    mem = sqlite3.connect(":memory:")
    sqlite3.connect(LEGACY).backup(mem)
    safari = [
        "SELECT * FROM maint_job WHERE technician = 'Beier'",
        "SELECT * FROM machine WHERE machine_name = 'cnc-02'",
        "SELECT * FROM maint_job WHERE technician LIKE '%ei%'",
    ]
    say("-- before the index")
    for q in safari:
        say(f"  {q}\n{plan(mem, q)}")
    mem.execute("CREATE INDEX ix_job_tech ON maint_job(technician)")
    say("-- after CREATE INDEX ix_job_tech ON maint_job(technician)")
    for q in safari:
        say(f"  {q}\n{plan(mem, q)}")
    breakers = [
        "SELECT * FROM maint_job WHERE lower(technician) = 'beier'",
        "SELECT * FROM maint_job WHERE technician LIKE 'Bei%'",
    ]
    say("-- trying to defeat the index on purpose")
    for q in breakers:
        say(f"  {q}\n{plan(mem, q)}")
else:
    say("Module02/legacy.db not found: rebuild it with  sh Module02/setup_legacy.sh")

# ---------------------------------------------------------------- Task 1
DASHBOARD = """
SELECT c.city, COUNT(DISTINCT c.customer_id) AS customers,
       SUM(ol.qty * p.price) AS revenue
FROM customer c
JOIN orders o     ON o.customer_id = c.customer_id
JOIN order_line ol ON ol.order_id = o.order_id
JOIN product p    ON p.product_id = ol.product_id
WHERE o.ordered_on >= '2025-01-01' AND o.ordered_on < '2026-01-01'
GROUP BY c.city
ORDER BY revenue DESC
"""
say("\n" + "=" * 70)
say("TASK 1: the dashboard query (reference version from the module)")
say("=" * 70)
for row in conn.execute(DASHBOARD):
    say(f"  {row}")
say("-- plan")
say(plan(conn, DASHBOARD))

if LLM_SQL.exists():
    llm = LLM_SQL.read_text().strip().rstrip(";")
    say("\n-- the LLM's query (Module03/llm_query.sql)")
    try:
        for row in conn.execute(llm):
            say(f"  {row}")
        say("-- plan")
        say(plan(conn, llm))
    except sqlite3.Error as e:
        say(f"  ERROR: {e}")
else:
    say("\n(no Module03/llm_query.sql yet: paste the LLM's SQL there and run again)")

# ---------------------------------------------------------------- Task 2
DAY = """
SELECT o.order_id, o.ordered_on, c.name
FROM orders o JOIN customer c ON c.customer_id = o.customer_id
WHERE o.ordered_on = '2026-02-14'
"""
DAY_FUNC = DAY.replace("o.ordered_on = '2026-02-14'", "date(o.ordered_on) = '2026-02-14'")
PRODUCT = "SELECT COUNT(*) FROM order_line WHERE product_id = 42"

say("\n" + "=" * 70)
say("TASK 2: index benchmark (median of 3 runs; single-day query batched x200)")
say("=" * 70)
for ix in ("ix_orders_ordered_on", "ix_orderline_order", "ix_orderline_product"):
    conn.execute(f"DROP INDEX IF EXISTS {ix}")

steps = [
    ("baseline (no extra index)", None),
    ("+ ix_orders_ordered_on", "CREATE INDEX ix_orders_ordered_on ON orders(ordered_on)"),
    ("+ ix_orderline_order", "CREATE INDEX ix_orderline_order ON order_line(order_id)"),
    ("+ ix_orderline_product", "CREATE INDEX ix_orderline_product ON order_line(product_id)"),
]
table = []
for label, ddl in steps:
    if ddl:
        conn.execute(ddl)
    conn.execute(DASHBOARD).fetchall()            # warm-up run pays for the file cache
    dash, dash_all = median_ms(conn, DASHBOARD)
    day, _ = median_ms(conn, DAY, batch=200)
    table.append((label, dash, day))
    say(f"\n## {label}")
    say(f"dashboard: median {dash:.1f} ms  (runs: {', '.join(f'{t:.1f}' for t in dash_all)})")
    say(plan(conn, DASHBOARD))
    say(f"single-day lookup: median {day:.3f} ms")
    say(plan(conn, DAY))

say("\n-- summary table (ms, median of 3)")
say(f"{'step':28s} {'dashboard':>10s} {'single-day':>11s}")
for label, dash, day in table:
    say(f"{label:28s} {dash:10.1f} {day:11.3f}")

say("\n-- negative result 1: a function around the column defeats the index")
say(f"  date(o.ordered_on) = '2026-02-14'\n{plan(conn, DAY_FUNC)}")
say("\n-- ix_orderline_product IS used when a query filters on product_id directly")
say(f"  {PRODUCT}\n{plan(conn, PRODUCT)}")

# ---------------------------------------------------------------- Task 3
conn.close()
say("\n" + "=" * 70)
say("TASK 3: injection drill (Module03/injection_demo.py)")
say("=" * 70)
demo = subprocess.run([sys.executable, str(HERE / "injection_demo.py")],
                      capture_output=True, text=True)
say(demo.stdout.rstrip())
if demo.stderr:
    say(demo.stderr.rstrip())

OUT.write_text("\n".join(lines) + "\n")
print(f"\nSaved everything to {OUT}")
