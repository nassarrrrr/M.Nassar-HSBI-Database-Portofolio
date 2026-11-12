# Reflection 6b: Module 6b (Polyglot Persistence & the Decision)

## Take-away: what do I want to remember?
- A JSON column is still a designed schema: `CHECK (json_valid(meta))` rejected broken JSON, and a new vendor field was queryable without a migration.
- An expression index only works if the query uses exactly the same expression: `json_extract(meta, '$.vendor')` used the index, `meta ->> '$.vendor'` did a full SCAN.
- For "get and set by key", SQLite was just as fast to read and 100× faster to write (in one batch) than `shelve`, and it can also answer questions across all sessions.
- There is no single best engine: SQLite for writes and lookups, DuckDB on Parquet for big reports, and a server only when many users must write over a network.

## What was good?
- Writing the decision record with my own numbers from 6a and 6b, instead of opinions.

## What was difficult, where did I struggle?
- Understanding why two expressions that give the same answer do not share an index.
- Explaining ACID, BASE and CAP with the systems I actually ran.

## Was there any good struggling or exploration?
- `shelve` turned out to use SQLite internally on Python 3.14, but with one commit per key. That explained its slow writes (13.9 s against 0.14 s).

## Interaction with peers and instructors
Bench 3 (the PostgreSQL server) and the peer defence of the decision record happen in class.

## Help and extra work
I used an AI assistant (Claude) to explain the concepts and to write the runner. All numbers come from my own runs in [6b results.txt](../Module06b/results.txt) and [6a results.txt](../Module06a/results.txt).

## Status
Benches 1, 2 and 4 are done. Bench 3 (server observations) and the defence notes are still open.
