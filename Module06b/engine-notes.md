# Module 6b: Engine notes

Raw numbers: [results.txt](results.txt) (6b) and [../Module06a/results.txt](../Module06a/results.txt) (6a).

## Bench 1: JSON
- **Why is the index ignored for `->>`?** An expression index is only used when the query repeats the *exact* indexed expression; `meta ->> '$.vendor'` is a different expression from `json_extract(meta, '$.vendor')`, even though both return the same value.
- **What if `vendor` became a real column?** Gain: column typing, a normal index, and cheap joins. Loss: the next vendor field needs a migration again, which is what Anke wanted to avoid. A sensible middle way is to promote only the keys everyone filters on, such as `vendor`, and keep the rest in JSON.
- **"NoSQL" does not mean "no schema":** `CHECK (json_valid(meta))` rejected broken JSON, which is the Module 4 constraint idea applied to a flexible column.

## Bench 2: key-value
- **Which number decides?** The writes: 13.874 s for `shelve` against 0.138 s for SQLite, while reads are the same order (0.6 s and 0.8 s).
- **One thing SQLite can do that `shelve` cannot:** "How many users filtered by each city?" One `GROUP BY` in 55.8 ms; `shelve` needs a Python loop over every key (504 ms).
- **Curiosity:** on Python 3.14, `shelve` itself stores its data in SQLite (`dbm.sqlite3`), but one commit per key.

## Bench 3: the server
*Not yet: this is done in class on the instructor's PostgreSQL server.* To fill in afterwards:
- **Easier:**
- **Harder:**
- **A failure mode an embedded database does not have:**
- **What happened with two writers on the same row:**

**ACID, BASE and CAP, in terms of what I ran:**
- **ACID:** SQLite gave me full transactions. The UPSERT in Module 4 and the 50,000-row `executemany` either commit completely or not at all.
- **BASE:** the Parquet copy from 6a behaves like BASE. It is available and fast, but only *eventually* consistent: it is as fresh as the last `refresh.py` run.
- **CAP:** SQLite sidesteps CAP by not being distributed: one file, one machine, no network partition. A PostgreSQL server reached over the network has to live with partitions: when the network or server is down, clients cannot get an answer.

## Bench 4: engine decision record for Kortmann
| Workload | Engine | Why | Evidence | Cost accepted | If the copy is stale |
|---|---|---|---|---|---|
| Sensor/job ingest, every 30 s, crash must not lose rows | **SQLite** | Transactions, constraints, UPSERT, row-at-a-time speed | 1,000 single inserts: SQLite 3.6 ms, DuckDB 1,085.6 ms (6a); constraints and UPSERT proven in Module 4 | One writer at a time | — (this *is* the source of truth) |
| Month-end report over two years | **DuckDB on a Parquet copy** | Columnar scan of 4 of 7 columns | Monthly report 2,606.7 ms in SQLite, 25.6 ms in DuckDB (102×); file 2.4 MB vs 112.65 MB (6a) | A second copy; nightly rebuild (~8 s) | The report misses the newest jobs; `refresh.py --check` compares row count and total, but not freshness |
| Vendor metadata that gains fields | **SQLite JSON column** + `json_valid` + expression index | New fields without a migration | New key queryable at once; index gives `SEARCH` (6b) | No column types inside JSON; the query must repeat the indexed expression exactly | — (one copy) |
| Dashboard session state | **SQLite key-value table** | Same read speed, much faster batched writes, and it can be queried | 50,000 writes: SQLite 0.138 s, `shelve` 13.874 s; cross-session query 55.8 ms (6b) | A tiny bit more code than a dict-like store | — (sessions are disposable) |
| *(optional)* Concurrent users on the network | **PostgreSQL server** | Many writers at once, network access, users and roles | *Bench 3 observation still to be added*; SQLite allows only one writer at a time (Module 1 table) | A server to run, secure and back up; a new failure mode when it is down | Depends on replication |

**If Kortmann could run only one engine, which would it be, and what would break first?**
> **SQLite.** It handles the ingest, the metadata and the sessions on its own, with the measured numbers above. What breaks first is the **month-end report**: on two years of history it takes about 2.6 s per run instead of 25.6 ms, and while it scans, the single writer waits. On the production dataset that is Lea's 40-minute report again. The second thing to break would be many concurrent writers on the network, which needs a server.

## Defence notes
*Not yet: swap records with another pod in class (12 minutes each way). To record: which question they asked, which row I changed (if any), and why.*
