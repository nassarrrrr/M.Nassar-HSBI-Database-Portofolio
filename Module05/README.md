# Module 5: Normalization vs. Denormalization

## Learning goals
1. Derive functional dependencies from a relation and identify candidate keys.
2. Normalize a relation to 1NF, 2NF, and 3NF, explaining the anomaly each step removes.
3. Denormalize deliberately to speed up a hot read path, and predict what it costs on writes and storage.
4. Measure the trade-off: query latency, write cost, and database size, before and after.
5. Decide, and defend, where a schema should sit on the normalization spectrum for a given workload.

## Files
- Flat 200k-row table: [setup.sql](setup.sql)
- 3NF decomposition: [normalize.sql](normalize.sql)
- Denormalized report table: [report.sql](report.sql)
- The whole lab in one run (Rounds 2–5 and the DuckDB stretcher): [run_module5.py](run_module5.py). Run it from the repo root with `uv run python Module05/run_module5.py`
- All raw output: [results.txt](results.txt)
- FDs, ER sketches, anomalies and curiosities: [normalization-notes.md](normalization-notes.md)
- Reflection: [Reflection 5](../Reflections/ref05.md)

## Round 1 and 2: dependencies and anomalies
See [normalization-notes.md](normalization-notes.md). In short: one site change touched **3 rows** in the five-row table, a new part could only be stored as a fake job row full of NULLs, and deleting job 1 erased the price of P-0002.

## Round 3: build it
| Table | Rows |
|---|---|
| flat_jobpart | 200,000 |
| machine | 50 |
| part | **10** |
| job | 20,000 |
| job_part | 200,000 |

**Integrity check:** `flat_rows = 200000, normalized_rows = 200000`, a match. Joining the four tables back together also gives exactly 200,000 rows, so the decomposition lost nothing. With `PRAGMA foreign_keys = ON` it still loads, with 0 foreign-key problems.

**Why `part` has 10 rows, not 40:** each job gets k = 1 … 10, and the part number is `(k % 40) + 1`. So only P-0002 … P-0011 ever appear. The `% 40` never wraps around, and P-0001 is never used.

## Round 4: race it
Both queries return the same 350 rows with the same total cost (722,610.0).

**Plan A (normalized, four-way join):**
```
SCAN jp
SEARCH j USING INTEGER PRIMARY KEY (rowid=?)
SEARCH m USING INDEX sqlite_autoindex_machine_1 (machine_id=?)
SEARCH p USING INDEX sqlite_autoindex_part_1 (part_no=?)
USE TEMP B-TREE FOR GROUP BY
```
**Plan B (denormalized, with `ix_report_machine`):**
```
SCAN report_jobpart USING INDEX ix_report_machine
USE TEMP B-TREE FOR GROUP BY
```
Timings are warm (one untimed run first), alternating A and B, median of 3.

## Round 5: price it
| Design | Dashboard query (ms) | Rows changed by one site update | Storage (KB) | Redundancy? |
|---|---|---|---|---|
| Normalized (3NF) | 88.2 | **1** (0.330 ms) | 3,976 | none |
| Denormalized (report, with index) | 90.2 | **4,000** (13.242 ms) | 10,832 + 2,920 index | site/technician/price repeated |
| Denormalized (report, index dropped) | **64.0** | 4,000 | 10,832 | site/technician/price repeated |

**What the numbers say:**
- **With its index, the denormalized table was not faster** (90.2 ms vs 88.2 ms). The plan `SCAN ... USING INDEX` walks the whole index and then fetches every row from the table.
- **Dropping the index made it about 27% faster** than the normalized query (64.0 ms). The index was hurting this query, not helping.
- **The price:** the report table is **2.7× bigger** (10,832 KB vs 3,976 KB, plus 2,920 KB for the index), and moving one machine to another site changes **4,000 rows instead of 1**, which is about 40× slower (13.2 ms vs 0.33 ms).
- **When the join gets harder,** denormalization pays more: with two extra dimensions (vendor, site region), the six-way join took **171.5 ms** and the wide table **127.9 ms**.

**DuckDB stretcher:** the same dashboard took **27.6 ms** (normalized) and **16.1 ms** (denormalized) in DuckDB, about 3–6× faster than SQLite for both designs. A columnar engine shrinks the problem the report table was built to solve. DuckDB also refused the query as written, because `site` is selected but not in `GROUP BY`. SQLite silently allows that.

## Round 6: recommendation to the operations lead
> **To: Yasmin Kaya, operations lead**
>
> Keep the transactional tables (machine, part, job, job_part) in 3NF. There, changing a machine's site touches 1 row in 0.33 ms, instead of 4,000 rows in 13.2 ms in the copied table, and no copy can disagree with another. On our 200,000-row test, the denormalized report table did not speed up the dashboard as built: 90.2 ms versus 88.2 ms for the normalized four-way join. Only after dropping its index was it faster, at 64.0 ms, about 27% better, while using 2.7 times the storage. So today I recommend serving the dashboard from the normalized tables. If the dashboard grows more dimensions, the report table becomes worth it: with two extra dimensions it was 25% faster (127.9 ms versus 171.5 ms). In that case build it without the machine index and keep it fresh in two ways: an `AFTER UPDATE` trigger on `machine` and `job` that copies a changed site or technician into the report rows (as in Module 4), plus a full rebuild inside one transaction every night to catch anything the triggers miss. For heavy analytics, a columnar engine like DuckDB answered the same query in 16–28 ms, which may remove the need for the copy altogether.
