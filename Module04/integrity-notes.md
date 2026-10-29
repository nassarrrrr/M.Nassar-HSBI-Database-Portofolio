# Module 4: Integrity notes

## 1. References I used (and the concept each taught me)
| Source | Concept I understood best from it |
|---|---|
| [sqlite.org/foreignkeys.html](https://sqlite.org/foreignkeys.html) | Foreign keys are off by default and must be enabled per connection |
| [sqlite.org/stricttables.html](https://www.sqlite.org/stricttables.html) | A STRICT table rejects values of the wrong type instead of storing them anyway |
| [sqlite.org/gencol.html](https://www.sqlite.org/gencol.html) | A generated column is computed by the engine from other columns |
| [sqlite.org/lang_upsert.html](https://www.sqlite.org/lang_upsert.html) | `ON CONFLICT ... DO UPDATE` turns a duplicate insert into an update |

## 2. The three layers of integrity
| Layer | Question | SQL mechanism | My example |
|---|---|---|---|
| Entity | Is every row identifiable and complete? | PRIMARY KEY, NOT NULL, UNIQUE | A second `temp_c` sensor for cnc-01 was rejected |
| Referential | Does a relationship point at something that exists? | FOREIGN KEY | A reading for sensor 99 was rejected |
| Domain (semantic) | Does the value make sense? | CHECK, STRICT, generated columns, triggers | 9000 °C was rejected |

## 3. Task A: the acceptance test
**Unconstrained table:** all 7 junk rows were stored, including 9000 °C, the text `'hot'` in a REAL column, `'abc'` as a sensor id, an all-NULL row, and the metric `'bogus'`. Nothing complained.

**The same table with constraints** (`STRICT`, `NOT NULL`, `CHECK(metric IN (...))`, `CHECK(value BETWEEN -273.15 AND 5000)`), one insert at a time:

| Insert | Result | Layer |
|---|---|---|
| `(1,'temp_c',9000)` | `CHECK constraint failed: value BETWEEN -273.15 AND 5000` | Domain |
| `(1,'temp_c','hot')` | `cannot store TEXT value in REAL column t2.value` | Domain (STRICT) |
| `(2,'bogus',-500)` | `CHECK constraint failed: metric IN (...)` | Domain |
| `('abc','temp_c',20)` | `cannot store TEXT value in INTEGER column t2.sensor_id` | Domain (STRICT) |
| `(NULL,'temp_c',20)` | `NOT NULL constraint failed: t2.sensor_id` | Entity |
| `(1,'Temp_C',20)` | `CHECK constraint failed: metric IN (...)` | Domain |
| `(1,'temp_c',NULL)` | **Accepted** | — |
| `(1,'temp_c','20')` | **Accepted**, stored as the number 20.0 | — |
| `(1,'temp_c',4999)` | **Accepted** | — |

## 4. Remarkable things
- **CHECK lets NULL through.** `CHECK(value BETWEEN ...)` is "unknown" for NULL, and SQLite only rejects a row when the check is *false*. To forbid a missing value, the column also needs `NOT NULL`.
- **STRICT is not as strict as it sounds.** The text `'20'` was accepted into a REAL column, because SQLite can convert it to 20.0 without losing anything. Only text that is not a number, like `'hot'`, is rejected.
- **A plausible but wrong value gets through.** 4999 °C passes every rule. Constraints catch impossible values, not wrong ones.
- **CHECK is case-sensitive:** `'Temp_C'` is rejected even though it means the same thing.
- **The foreign key only works when switched on.** The same orphan reading for sensor 99 was accepted on a connection without `PRAGMA foreign_keys = ON`.

## 5. LLM Q&A
| Prompt (to Claude) | Short answer | How I verified it |
|---|---|---|
| "Does a CHECK constraint stop NULL?" | No; NULL makes the check unknown, which counts as a pass | Inserted `(1,'temp_c',NULL)`: accepted |
| "Which can reject a row, a BEFORE or an AFTER trigger?" | Both can with `RAISE(ABORT, ...)`, but BEFORE is the usual choice | Not tested yet (Task 5 stretcher) |
| "Why is `PRAGMA foreign_keys` per connection?" | For backward compatibility, it is off by default | A connection without it accepted the orphan reading |

## 6. Task B: share with another pod
*Not yet. To do with a neighbouring pod: compare the most surprising accepted row, and which constraint was hardest (CHECK with NULL is my candidate).*
