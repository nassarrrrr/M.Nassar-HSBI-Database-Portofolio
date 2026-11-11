# Reflection 5: Module 5 (Normalization vs. Denormalization)

## Take-away: what do I want to remember?
- A functional dependency must come from the real world, not from a few rows. In five rows, cnc-01 always had tech-0, but that is an accident, not a rule.
- 2NF removes columns that depend on only part of the key (`part_no → part_price`); 3NF removes columns that depend on another non-key column (`machine_id → site`).
- Copying data (denormalization) is a trade, not a free speedup. In my test, the copied table was only faster after I removed its index, and it cost 2.7× the storage.
- The real price of a copy is on writes: moving one machine to another site changed 1 row in 3NF but 4,000 rows in the report table.

## What was good?
- Causing the three anomalies by hand made them easy to understand: one update left cnc-01 in two cities at once.
- Seeing that the 4 normalized tables join back to exactly 200,000 rows proved that nothing was lost.

## What was difficult, where did I struggle?
- Deciding which dependencies are real and which only appear in the sample.
- Understanding why the "one table" dashboard was not faster. The joins were cheap because the small tables (50 machines, 10 parts) fit in memory.

## Was there any good struggling or exploration?
- The index on the report table made the dashboard slower (90.2 ms vs 64.0 ms without it).
- DuckDB refused a query that SQLite ran without complaint, because `site` was not in `GROUP BY`.

## Interaction with peers and instructors
The round gates (showing each artefact to a neighbouring pod) are still to be done in class.

## Help and extra work
I used an AI assistant (Claude) to explain the concepts and to write the script that runs the lab. All numbers in my notes and memo come from the real output in [results.txt](../Module05/results.txt), which I produced on my own laptop. The LLM diff of my FD list is still to do.

## Status
Rounds 1–6 and the DuckDB stretcher are done. Still open: the LLM diff of the FD list (Round 1) and the round gates with another pod.
