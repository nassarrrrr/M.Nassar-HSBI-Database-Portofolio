-- Round 3: decompose flat_jobpart into 3NF
DROP TABLE IF EXISTS job_part;
DROP TABLE IF EXISTS job;
DROP TABLE IF EXISTS part;
DROP TABLE IF EXISTS machine;

CREATE TABLE machine(machine_id TEXT PRIMARY KEY, site TEXT NOT NULL);
CREATE TABLE part(part_no TEXT PRIMARY KEY, part_price REAL NOT NULL);
CREATE TABLE job(job_id INTEGER PRIMARY KEY, machine_id TEXT NOT NULL
                 REFERENCES machine(machine_id), technician TEXT NOT NULL, done_on TEXT NOT NULL);
CREATE TABLE job_part(job_id INTEGER REFERENCES job(job_id),
                      part_no TEXT REFERENCES part(part_no),
                      PRIMARY KEY (job_id, part_no));

INSERT INTO machine SELECT DISTINCT machine_id, site FROM flat_jobpart;
INSERT INTO part    SELECT DISTINCT part_no, CAST(part_price AS REAL) FROM flat_jobpart;
INSERT INTO job     SELECT DISTINCT job_id, machine_id, technician, done_on FROM flat_jobpart;
INSERT INTO job_part SELECT DISTINCT job_id, part_no FROM flat_jobpart;
