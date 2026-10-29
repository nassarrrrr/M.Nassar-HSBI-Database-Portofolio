SELECT
    c.city,
    COUNT(DISTINCT c.customer_id) AS distinct_customers,
    SUM(ol.qty * p.price) AS total_revenue
FROM customer AS c
JOIN orders AS o
    ON o.customer_id = c.customer_id
JOIN order_line AS ol
    ON ol.order_id = o.order_id
JOIN product AS p
    ON p.product_id = ol.product_id
WHERE o.ordered_on >= '2025-01-01'
  AND o.ordered_on <  '2026-01-01'
GROUP BY c.city
ORDER BY total_revenue DESC;
