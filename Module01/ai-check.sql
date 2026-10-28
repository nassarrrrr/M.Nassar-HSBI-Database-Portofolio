.headers on
.mode column
-- A) The AI's query, exactly as given
SELECT machine, AVG(spindle_load) AS avg_spindle_load
FROM readings
WHERE time(ts) > '18:00:00'
GROUP BY machine
ORDER BY avg_spindle_load DESC;

-- B) Profile it: does it scan the whole table?
EXPLAIN QUERY PLAN
SELECT machine, AVG(spindle_load) AS avg_spindle_load
FROM readings
WHERE time(ts) > '18:00:00'
GROUP BY machine
ORDER BY avg_spindle_load DESC;

-- C) Check: which hours does the AI's filter really include?
SELECT MIN(time(ts)) AS first_time, MAX(time(ts)) AS last_time, COUNT(*) AS rows_used
FROM readings
WHERE time(ts) > '18:00:00';

-- D) Fixed version: overnight = 18:00 until 06:00 the next morning
SELECT machine, AVG(spindle_load) AS avg_spindle_load, COUNT(*) AS rows_used
FROM readings
WHERE time(ts) >= '18:00:00' OR time(ts) < '06:00:00'
GROUP BY machine
ORDER BY avg_spindle_load DESC;
