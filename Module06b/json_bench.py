# Module06b/json_bench.py — run with:  uv run python Module06b/json_bench.py
"""A JSON column in SQLite: store flexibly, query precisely, index deliberately."""
import sqlite3
from pathlib import Path

here = Path(__file__).parent
con = sqlite3.connect(here / "polyglot.db")

con.executescript("""
DROP TABLE IF EXISTS device;
CREATE TABLE device(
    device_id INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    meta      TEXT NOT NULL CHECK (json_valid(meta))   -- it *is* JSON, enforced
) STRICT;

INSERT INTO device(name, meta) VALUES
  ('cnc-01',   '{"vendor":"Siemens","firmware":"4.2","calibrated":"2026-01-10"}'),
  ('cnc-02',   '{"vendor":"Fanuc","firmware":"3.9"}'),
  ('molder-07','{"vendor":"Arburg","firmware":"8.1","calibrated":"2025-11-02","nozzle_mm":2.5}');
""")

print("-- a path behaves like a column")
for row in con.execute("SELECT name, json_extract(meta, '$.vendor') FROM device"):
    print(row)

print("-- the ->> shorthand returns a scalar")
for row in con.execute("SELECT name, meta ->> '$.firmware' FROM device"):
    print(row)

print("-- an object becomes rows")
for row in con.execute(
        "SELECT d.name, j.key, j.value FROM device d, json_each(d.meta) j "
        "WHERE d.name = 'cnc-01'"):
    print(row)

print("-- index the path you filter on, then prove it")
con.executescript("""
CREATE INDEX ix_device_vendor ON device(json_extract(meta, '$.vendor'));
""")
print(con.execute(
    "EXPLAIN QUERY PLAN SELECT name FROM device "
    "WHERE json_extract(meta, '$.vendor') = 'Fanuc'").fetchall())

print("-- now break it: the shorthand is a different expression")
print(con.execute(
    "EXPLAIN QUERY PLAN SELECT name FROM device "
    "WHERE meta ->> 'vendor' = 'Fanuc'").fetchall())
