.headers on
.mode column
.timer on
-- 1. How many readings per machine?
SELECT machine, COUNT(*) AS n FROM readings GROUP BY machine;

-- 2. What was the peak vibration per machine?
SELECT machine, MAX(vib_rms) AS peak_vib FROM readings GROUP BY machine;

-- 3. How many readings exceeded the 2.0 mm/s vibration alarm?
SELECT COUNT(*) AS alarms FROM readings WHERE vib_rms > 2.0;
