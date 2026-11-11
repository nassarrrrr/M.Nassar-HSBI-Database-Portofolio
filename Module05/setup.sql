-- Round 3: the deliberately unnormalized table (~200k rows)
DROP TABLE IF EXISTS flat_jobpart;
CREATE TABLE flat_jobpart (
    job_id      INTEGER,
    machine_id  TEXT,
    site        TEXT,           -- transitive dependency machine_id -> site
    technician  TEXT,
    part_no     TEXT,
    part_price  TEXT,           -- partial dependency part_no -> part_price, and TEXT!
    done_on     TEXT
);

-- ~200k rows: 20k jobs x exactly 10 parts
WITH RECURSIVE j(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM j WHERE n < 20000),
               p(k) AS (SELECT 1 UNION ALL SELECT k+1 FROM p WHERE k < 10)
INSERT INTO flat_jobpart
SELECT n,
       'cnc-' || printf('%02d', (n % 50) + 1),
       CASE (n % 50) WHEN 0 THEN 'Bielefeld' ELSE 'Gütersloh' END,
       'tech-' || (n % 7),
       'P-' || printf('%04d', (k % 40) + 1),
       printf('%.2f', 5 + (k % 40)),
       date('2026-01-01', '+' || (n % 90) || ' days')
FROM j CROSS JOIN p;

CREATE INDEX ix_flat_machine ON flat_jobpart(machine_id);
