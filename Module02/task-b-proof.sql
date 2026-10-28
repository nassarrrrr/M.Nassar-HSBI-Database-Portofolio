.headers on
.mode column
CREATE TABLE work_order (order_id INTEGER PRIMARY KEY, title TEXT NOT NULL);
CREATE TABLE part (part_no TEXT PRIMARY KEY, description TEXT NOT NULL);
CREATE TABLE order_part (
    order_id INTEGER REFERENCES work_order(order_id),
    part_no  TEXT REFERENCES part(part_no),
    PRIMARY KEY (order_id, part_no)
);
INSERT INTO work_order VALUES (1, 'Replace bearing'), (2, 'Belt service');
INSERT INTO part VALUES ('P-1001', 'Ball bearing'), ('P-1002', 'Spindle belt');
INSERT INTO order_part VALUES (1, 'P-1001'), (1, 'P-1002'), (2, 'P-1002');

-- one order uses many parts
SELECT order_id, COUNT(*) AS parts FROM order_part GROUP BY order_id;
-- one part is used by many orders
SELECT part_no, COUNT(*) AS orders FROM order_part GROUP BY part_no;
