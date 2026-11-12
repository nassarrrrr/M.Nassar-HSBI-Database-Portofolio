# Module 6b: Polyglot Persistence & the Decision

## Learning goals
1. Store **semi-structured data (JSON)** in SQLite and query it with `json_extract`/`json_each` and an **expression index**.
2. Implement and evaluate a **key-value access pattern** against SQLite.
3. Explain **ACID vs. BASE** and the **CAP theorem** in terms of the systems you actually ran.
4. Choose an engine per workload and **defend the choice with a measurement**.
5. Say what changes, and what gets harder, when the same data lives on a **server**.

## Files
- Bench 1: [json_bench.py](json_bench.py)
- Bench 2: [kv_compare.py](kv_compare.py)
- Both benches plus extra checks in one run: [run_module6b.py](run_module6b.py). Run it from the repo root with `uv run python Module06b/run_module6b.py`
- All raw output: [results.txt](results.txt)
- Notes, server observations and **the decision record**: [engine-notes.md](engine-notes.md)
- Reflection: [Reflection 6b](../Reflections/ref06b.md)

## Bench 1: metadata as JSON
The `device` table stores vendor metadata in a `meta` column with `CHECK (json_valid(meta))`.

| Check | Result |
|---|---|
| `json_extract(meta, '$.vendor')` | Works like a column: Siemens, Fanuc, Arburg |
| `json_each(meta)` for cnc-01 | The object becomes 3 rows: vendor, firmware, calibrated |
| Insert `'{vendor: Siemens'` (not JSON) | **Rejected:** `CHECK constraint failed: json_valid(meta)` |
| A vendor adds `spindle_rpm_max` | Queryable at once, **no migration**; older devices return NULL |

**The expression index**, `CREATE INDEX ix_device_vendor ON device(json_extract(meta, '$.vendor'))`:

| Filter written as | Rows | Plan |
|---|---|---|
| `json_extract(meta, '$.vendor') = 'Fanuc'` | 1 | **`SEARCH device USING INDEX ix_device_vendor`** |
| `meta ->> '$.vendor' = 'Fanuc'` | 1 | `SCAN device` |
| `meta ->> 'vendor' = 'Fanuc'` | 1 | `SCAN device` |
| `meta ->> '$.vendor'`, after indexing *that* expression | 1 | `SEARCH device USING INDEX ix_device_vendor_arrow` |

**Why `->>` gives a SCAN:** SQLite only uses an expression index when the query contains *exactly the same expression* as the index; `meta ->> '$.vendor'` gives the same answer as `json_extract(meta, '$.vendor')`, but it is a different expression, so the index does not match.

## Bench 2: session state (50,000 sessions)
| | Set (write) 50,000 | Get (read) 50,000 |
|---|---|---|
| `shelve` (key-value) | **13.874 s** | 0.597 s |
| SQLite (`session(k PRIMARY KEY, v)`) | **0.138 s** (about 100× faster) | 0.796 s |

- **Reads tie** (both under a second, the same order of magnitude); **writes do not** (100×).
- **Why `shelve` writes so slowly:** on this machine `dbm.whichdb` reports `dbm.sqlite3`. Since Python 3.13 the default backend of `shelve` *is* SQLite, and it commits every single assignment, while SQLite proper wrote all 50,000 rows in one `executemany` transaction.
- **What SQLite can do that `shelve` cannot:** answer a question *across* sessions. "How many sessions and users per city filter?" is one `GROUP BY` in SQLite (55.8 ms; 12,500 sessions and 25 users per filter). `shelve` has no query language; a Python loop over every key took 504.0 ms.

**Choice for dashboard sessions:** SQLite. Reads are as fast, writes are 100× faster in a batch, and the data can be queried.

## Bench 3: the server
Done in class on the instructor's PostgreSQL server. Observations: [engine-notes.md](engine-notes.md#bench-3-the-server).

## Bench 4: the decision record
See [engine-notes.md](engine-notes.md#bench-4-engine-decision-record-for-kortmann).
