-- 1. JOIN: Total sales by store
SELECT s.store_name, SUM(t.total_amount) AS total_sales
FROM transaction t
JOIN store s ON t.store_id = s.store_id
GROUP BY s.store_name
ORDER BY total_sales DESC;

-- 2. JOIN + AGGREGATE: Top-selling products by quantity
SELECT p.product_name, SUM(ti.quantity) AS total_sold
FROM transaction_item ti
JOIN product p ON ti.product_id = p.product_id
GROUP BY p.product_name
ORDER BY total_sold DESC
LIMIT 5;

-- 3. NESTED QUERY: Customers who spent above the average total
SELECT customer_name
FROM customer
WHERE customer_id IN (
    SELECT customer_id
    FROM transaction
    GROUP BY customer_id
    HAVING SUM(total_amount) > (SELECT AVG(total_amount) FROM transaction)
);

-- 4. NESTED QUERY: Products currently below reorder level at any store
SELECT p.product_name, i.quantity_on_hand, p.reorder_level
FROM inventory i
JOIN product p ON i.product_id = p.product_id
WHERE i.quantity_on_hand < p.reorder_level;

-- 5. VIEW: Reusable view for supplier product performance
CREATE VIEW supplier_product_summary AS
SELECT sup.company_name, p.product_name, SUM(ti.quantity) AS total_units_sold
FROM transaction_item ti
JOIN product p ON ti.product_id = p.product_id
JOIN supplier sup ON p.supplier_id = sup.supplier_id
GROUP BY sup.company_name, p.product_name;

-- Then query it:
SELECT * FROM supplier_product_summary ORDER BY total_units_sold DESC;

-- 6. AGGREGATE + JOIN: Return rate by product
SELECT p.product_name,
       COUNT(tr.return_id) AS total_returns,
       SUM(tr.refund_amount) AS total_refunded
FROM transaction_return tr
JOIN transaction_item ti ON tr.transaction_item_id = ti.transaction_item_id
JOIN product p ON ti.product_id = p.product_id
GROUP BY p.product_name
ORDER BY total_refunded DESC;

-- 7. RETURNS: Employees who processed the most returned transactions
SELECT e.employee_name, s.store_name,
       COUNT(tr.return_id) AS total_returns_processed,
       SUM(tr.refund_amount) AS total_refund_amount
FROM transaction_return tr
JOIN transaction_item ti ON tr.transaction_item_id = ti.transaction_item_id
JOIN transaction t ON ti.transaction_id = t.transaction_id
JOIN employee e ON t.employee_id = e.employee_id
JOIN store s ON e.store_id = s.store_id
GROUP BY e.employee_name, s.store_name
ORDER BY total_returns_processed DESC;

-- 8. HIRED (NOT YET PROMOTED) EMPLOYEE: nested query using NOT EXISTS
SELECT e.employee_name, e.role, s.store_name
FROM employee e
JOIN store s ON e.store_id = s.store_id
WHERE NOT EXISTS (
    SELECT 1
    FROM employee_role_history erh
    WHERE erh.employee_id = e.employee_id
);

-- 9. PROMOTED EMPLOYEE: employees with a promotion history, showing role progression
SELECT e.employee_name, s.store_name,
       erh.previous_role, erh.new_role, erh.promotion_date
FROM employee_role_history erh
JOIN employee e ON erh.employee_id = e.employee_id
JOIN store s ON e.store_id = s.store_id
ORDER BY erh.promotion_date DESC;

