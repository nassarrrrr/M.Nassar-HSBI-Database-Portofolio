.headers on
.mode column
.timer on

-- CARDINALITY 1: how many parts does each job hide in parts_used?
SELECT job_id, parts_used,
       LENGTH(parts_used) - LENGTH(REPLACE(parts_used, ',', '')) + 1 AS n_parts
FROM maint_job;

-- CARDINALITY 2: one machine has many jobs (1:n)
SELECT machine_name, COUNT(*) AS jobs FROM maint_job GROUP BY machine_name;

-- CARDINALITY 3: one technician does many jobs (1:n)
SELECT technician, COUNT(*) AS jobs FROM maint_job GROUP BY technician;

-- DEFECT 1: orphan jobs (machine does not exist)
SELECT m.job_id, m.machine_name
FROM maint_job m
LEFT JOIN machine x ON m.machine_name = x.machine_name
WHERE x.machine_name IS NULL;

-- DEFECT 2: duplicate part numbers
SELECT part_no, COUNT(*) AS copies
FROM part GROUP BY part_no HAVING COUNT(*) > 1;

-- DEFECT 3: price stored as text, so the comparison is wrong
SELECT part_no, unit_price FROM part WHERE unit_price < '15';

-- DEFECT 4: install dates that are not dates
SELECT machine_name, installed FROM machine
WHERE installed NOT GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]';

-- DEFECT 5: joining on the list loses multi-part jobs
SELECT j.job_id, p.description
FROM maint_job j
JOIN part p ON p.part_no = j.parts_used;