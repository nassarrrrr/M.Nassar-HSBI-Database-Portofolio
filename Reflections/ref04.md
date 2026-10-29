# Reflection 4: Module 4 (Data Integrity, Constraints & Edge Triggers)

## Take-away: what do I want to remember?
- A database without constraints accepts anything: 9000 °C, `'hot'` as a temperature, and a reading for a sensor that does not exist.
- There are three layers of integrity: entity (keys, NOT NULL, UNIQUE), referential (FOREIGN KEY) and domain (CHECK, STRICT, triggers).
- A constraint is only real once I have seen it reject something.
- `PRAGMA foreign_keys = ON` must be set on every connection. Without it, the foreign key does nothing.
- UPSERT (`ON CONFLICT ... DO UPDATE`) makes ingestion safe to replay: running the loader twice still gave 11 rows.

## What was good?
- Seeing each bad insert fail with a clear error made the three layers concrete.
- The triggers did their work automatically: one insert created an alarm, one update created an audit row.

## What was difficult, where did I struggle?
- Understanding why a CHECK constraint accepts NULL, and that I need NOT NULL as well.
- Understanding why file permissions are fine for an edge gateway but not for a web app with many users.

## Was there any good struggling or exploration?
- STRICT accepted the text `'20'` because it converts cleanly to a number. "Strict" does not mean "only exact types".
- The alarm trigger made 10,000 inserts about 2.5× slower (11.7 ms to 29.6 ms). A trigger on the ingest path is a real cost, not a free extra.

## Interaction with peers and instructors
Task B (sharing with another pod) is still to be done in class.

## Help and extra work
I used an AI assistant (Claude) to explain the concepts and to write the script that runs the lab. Every result in my notes comes from the real output in [results.txt](../Module04/results.txt), which I produced on my own laptop.

## Status
Tasks A, 1, 2, 3 and 4 are done. Task B (pod exchange) is not yet done, and the Task 5 stretcher is skipped.
