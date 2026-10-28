sqlite3 Module02/legacy.db <<'SQL'
DROP TABLE IF EXISTS machine;
DROP TABLE IF EXISTS part;
DROP TABLE IF EXISTS maint_job;

CREATE TABLE machine (
    machine_name TEXT,
    serial_no    TEXT,
    site         TEXT,
    installed    TEXT
);

CREATE TABLE part (
    part_no      TEXT,
    description  TEXT,
    unit_price   TEXT
);

CREATE TABLE maint_job (
    job_id       INTEGER,
    machine_name TEXT,
    technician   TEXT,
    done_on      TEXT,
    parts_used   TEXT
);

INSERT INTO machine VALUES
  ('cnc-01','SN-88120','Gütersloh','2019-03-11'),
  ('cnc-02','SN-88121','Gütersloh','2019-03-11'),
  ('cnc-03','SN-88122','Bielefeld','2021-07-02'),
  ('RANDOM-NAME','SN-90000','Gütersloh','unknown');

INSERT INTO part VALUES
  ('P-1001','Ball bearing 6203','12.50'),
  ('P-1002','Spindle belt','48.00'),
  ('P-1003','Coolant filter','9.90'),
  ('P-1003','Coolant filter','9.90');

INSERT INTO maint_job VALUES
  (1,'cnc-01','Beier','2026-01-08','P-1001,P-1002'),
  (2,'cnc-02','Klaas','2026-02-14','P-1003'),
  (3,'cnc-05','Beier','2026-02-20','P-1001'),
  (4,'cnc-01','Werther','2026-03-01',NULL);
SQL
