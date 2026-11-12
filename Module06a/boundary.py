# Module06a/boundary.py — run with:  uv run python Module06a/boundary.py
"""1,000 single-row writes and lookups: the workload DuckDB is not built for."""
import sqlite3
import time

import duckdb

N = 1_000


def run_sqlite():
    con = sqlite3.connect(":memory:")
    con.execute("CREATE TABLE s(id INTEGER PRIMARY KEY, k TEXT, v REAL)")
    t0 = time.perf_counter()
    for i in range(N):
        con.execute("INSERT INTO s VALUES (?, ?, ?)", (i, f"k{i}", i * 1.5))
    con.commit()
    insert = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    for i in range(N):
        con.execute("SELECT v FROM s WHERE id = ?", (i,)).fetchone()
    lookup = (time.perf_counter() - t0) * 1000
    return insert, lookup


def run_duckdb():
    con = duckdb.connect()
    con.execute("CREATE TABLE s(id INTEGER PRIMARY KEY, k TEXT, v DOUBLE)")
    t0 = time.perf_counter()
    for i in range(N):
        con.execute("INSERT INTO s VALUES (?, ?, ?)", (i, f"k{i}", i * 1.5))
    insert = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    for i in range(N):
        con.execute("SELECT v FROM s WHERE id = ?", (i,)).fetchone()
    lookup = (time.perf_counter() - t0) * 1000
    return insert, lookup


def run_duckdb_batched():
    """The fix a thoughtful student proposes: one executemany instead of 1,000 executes."""
    con = duckdb.connect()
    con.execute("CREATE TABLE s(id INTEGER PRIMARY KEY, k TEXT, v DOUBLE)")
    rows = [(i, f"k{i}", i * 1.5) for i in range(N)]
    t0 = time.perf_counter()
    con.executemany("INSERT INTO s VALUES (?, ?, ?)", rows)
    return (time.perf_counter() - t0) * 1000


si, sl = run_sqlite()
di, dl = run_duckdb()
db_ = run_duckdb_batched()
print(f"inserts sqlite {si:8.1f} ms | duckdb {di:8.1f} ms | duckdb executemany {db_:8.1f} ms")
print(f"lookups sqlite {sl:8.1f} ms | duckdb {dl:8.1f} ms")
