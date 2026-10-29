# Module 4: Data Integrity, Constraints & Edge Triggers

## Learning goals
1. Create tables with the full constraint toolkit: `NOT NULL`, `UNIQUE`, `CHECK`, `PRIMARY KEY`, `FOREIGN KEY`, and `STRICT` typing.
2. Use **generated columns** to derive values at the engine instead of in application code.
3. Write **triggers** that enforce domain rules and maintain audit/rollup tables automatically.
4. Use **DML** correctly, including `UPSERT` (`ON CONFLICT`) for idempotent edge ingestion.
5. Reason about **access control (DCL)**: who may read or write, and how that maps from server `GRANT`s to an embedded, local-first world.

## Files
- Schema with all constraints: [setup.sql](setup.sql)
- Alarm and audit tables and triggers: [triggers.sql](triggers.sql)
- Replay-safe CSV loader: [ingest.py](ingest.py), with test data [readings.csv](readings.csv)
- The whole lab in one run: [run_module4.py](run_module4.py). Run it from the repo root with `uv run python Module04/run_module4.py`
- All raw output: [results.txt](results.txt)
- Study notes: [integrity-notes.md](integrity-notes.md)
- Reflection: [Reflection 4](../Reflections/ref04.md)

## Task 1: proving the constraints work
Every rule was tested by trying to break it. Exact errors from [results.txt](results.txt):

| Insert | Result | Layer |
|---|---|---|
| Two sensors, and reading 41.5 for sensor 1 | Accepted | — |
| Temperature 9000 | `CHECK constraint failed: value >= -273.15 AND value <= 5000` | Domain (CHECK) |
| `'hot'` into the REAL `value` column | `cannot store TEXT value in REAL column reading.value` | Domain (STRICT type) |
| Reading for sensor 99 | `FOREIGN KEY constraint failed` | Referential |
| Second `temp_c` sensor for cnc-01 | `UNIQUE constraint failed: sensor.machine_id, sensor.metric` | Entity |
| `interval_s = 0` | `CHECK constraint failed: interval_s > 0` | Domain (CHECK) |

**Generated column:** for the valid reading, `energy_j = value × interval_s = 41.5 × 1 = 41.5`. The engine computes it, so no application can calculate it differently.

**Why `PRAGMA foreign_keys = ON` matters:** on a second connection without it, the same reading for the non-existent sensor 99 was **accepted**. Foreign keys are off by default and must be switched on for every connection.

## Task 2: idempotent ingestion with UPSERT
```sql
CREATE UNIQUE INDEX ux_reading_sensor_ts ON reading(sensor_id, ts);

INSERT INTO reading(sensor_id, ts, value, interval_s)
VALUES (1,'2026-03-01 08:00:00', 41.7, 1)
ON CONFLICT(sensor_id, ts) DO UPDATE SET value = excluded.value;
```
- The replayed reading did **not** create a second row; it corrected the value from 41.5 to 41.7.
- [ingest.py](ingest.py) loads [readings.csv](readings.csv) (10 rows) with `executemany` and the same UPSERT. **Run twice: 11 rows after the first run and still 11 after the second, 0 duplicate keys.**

## Task 3: triggers for alarms and audit
Trigger DDL: [triggers.sql](triggers.sql).
- **Alarm:** inserting vibration 2.7 on sensor 2 automatically created `(1, 2, '2026-03-01 09:00:00', 2.7, 'vibration over 2.0 mm/s')`.
- **Audit:** updating that value to 1.4 automatically recorded `(reading 12, old 2.7, new 1.4, time of change)`.

**Trigger cost** (10,000 vibration readings in one transaction, median of 3 runs):

| | Median | Alarms raised |
|---|---|---|
| Without alarm trigger | 11.7 ms | 0 |
| With alarm trigger | 29.6 ms | 2,664 |

The trigger makes ingestion about **2.5× slower** (+17.9 ms per 10,000 rows). Part of that is the 2,664 extra alarm inserts, and part is the sensor lookup in the `WHEN` clause, which runs for every row. That is still only about 3 µs per reading, so it is acceptable for a gateway, but it is a real cost on the hot ingest path.

## Task 4: access control without a server
1. **View:** `machine_health` shows only machine, metric, peak value and count. Result: `('cnc-01', 'temp_c', 42.3, 11)` and `('cnc-01', 'vib_rms', 1.4, 1)`.
2. **File level:** `chmod 444 Module04/edge.db` made the file `-r--r--r--`.
3. **Connection level:** with `mode=ro`, `SELECT COUNT(*)` returned 12, but `DELETE FROM reading` was rejected: `attempt to write a readonly database`. A normal connection on the read-only file was rejected the same way.
4. `chmod 644` restored write access.

**Comparison with PostgreSQL:** a PostgreSQL server has users and roles, so I could `GRANT SELECT ON machine_health TO reporter` and the server would check every query against that user's rights. SQLite has no users at all: whoever can open the file can do whatever the file permissions allow, and a view is only a convenience, because a reader with file access can still query the base tables. That is acceptable on an edge gateway, where one process writes, a few trusted people read, and the box sits locked in the plant. It is not acceptable for a multi-tenant web app, where many users reach the data through the same process, so every user would get the process's full file access unless the app code checked every request itself.
