# Task 7: Checking an AI-written query

## The prompt I used (ChatGPT)
> Here is my SQLite table: readings(ts TEXT, machine TEXT, temp_c REAL, vib_rms REAL, spindle_load REAL). Write a query that returns, for each machine, the average spindle load for readings taken overnight (after 18:00), ordered by average load descending.

## The SQL the AI gave me
```sql
SELECT machine, AVG(spindle_load) AS avg_spindle_load
FROM readings
WHERE time(ts) > '18:00:00'
GROUP BY machine
ORDER BY avg_spindle_load DESC;
```

## How I tested it
All tests are in [ai-check.sql](ai-check.sql), with the full output in [ai-check-results.txt](ai-check-results.txt).

1. **Run it:** it runs without errors. Result: cnc-03 60.43, cnc-01 60.37, cnc-02 60.36.
2. **Profile it:** `EXPLAIN QUERY PLAN` shows `SCAN readings`, so it reads the whole table (172,800 rows). An index on `ts` would not help, because the filter wraps `ts` in `time()`.
3. **Break it:** I checked which times the filter really includes. They run from 18:00:03 to 23:59:57, which is only 43,194 rows. The readings from midnight to 06:00 are missing, and so is 18:00:00 itself.

## Fixed query
```sql
SELECT machine, AVG(spindle_load) AS avg_spindle_load, COUNT(*) AS rows_used
FROM readings
WHERE time(ts) >= '18:00:00' OR time(ts) < '06:00:00'
GROUP BY machine
ORDER BY avg_spindle_load DESC;
```
Result: 86,400 rows (28,800 per machine). cnc-02 60.21, cnc-03 60.20, cnc-01 60.18.

## What the AI got right, what it got wrong, how I verified it
The AI got the syntax right: the query runs, `time(ts)` works on my timestamp format, and the grouping and sorting are correct. But it got the meaning of "overnight" wrong. Its filter `time(ts) > '18:00:00'` stops at midnight, so the hours from 00:00 to 06:00 are missing, and `>` also skips exactly 18:00:00. I found this by checking the first time, last time and row count that the filter really selects. It used 43,194 rows instead of 86,400. This changed the answer: the AI ranked cnc-03 highest, but the corrected query ranks cnc-02 highest. Lesson: a query that runs is not automatically correct. I have to check what data it really uses.
