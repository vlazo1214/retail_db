CREATE TABLE IF NOT EXISTS store (
    store_id SERIAL PRIMARY KEY,
    store_name VARCHAR(255) NOT NULL,
    address VARCHAR(255),
    phone VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS employee (
    employee_id SERIAL PRIMARY KEY,
    employee_name VARCHAR(255) NOT NULL,
    role VARCHAR(255) NOT NULL,
    store_id INTEGER NOT NULL REFERENCES store(store_id) ON DELETE RESTRICT
);

-- Added to support employee promotion tracking and history
CREATE TABLE IF NOT EXISTS employee_role_history (
    history_id SERIAL PRIMARY KEY,
    previous_role VARCHAR(255) NOT NULL,
    new_role VARCHAR(255) NOT NULL,
    promotion_date DATE NOT NULL DEFAULT CURRENT_DATE,
    termination_date DATE NOT NULL DEFAULT CURRENT_DATE,
    employee_id INTEGER NOT NULL REFERENCES employee(employee_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS customer (
    customer_id SERIAL PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS supplier (
    supplier_id SERIAL PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS product (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    category VARCHAR(255),
    unit_price FLOAT NOT NULL CHECK (unit_price >= 0),
    reorder_level INTEGER NOT NULL DEFAULT 10 CHECK (reorder_level >= 0), -- Changed to INTEGER for logical threshold checks
    supplier_id INTEGER NOT NULL REFERENCES supplier(supplier_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS inventory (
    inventory_id SERIAL PRIMARY KEY,
    quantity_on_hand INTEGER NOT NULL DEFAULT 0 CHECK (quantity_on_hand >= 0),
    last_updated DATE NOT NULL DEFAULT CURRENT_DATE,
    store_id INTEGER NOT NULL REFERENCES store(store_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES product(product_id) ON DELETE RESTRICT,
    CONSTRAINT unique_store_product UNIQUE (store_id, product_id) -- Prevents duplicate entries for the same product at a store
);

CREATE TABLE IF NOT EXISTS transaction (
    transaction_id SERIAL PRIMARY KEY,
    transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
    total_amount FLOAT NOT NULL DEFAULT 0.0 CHECK (total_amount >= 0),
    store_id INTEGER NOT NULL REFERENCES store(store_id) ON DELETE RESTRICT,
    employee_id INTEGER NOT NULL REFERENCES employee(employee_id) ON DELETE RESTRICT,
    customer_id INTEGER REFERENCES customer(customer_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS transaction_item (
    transaction_item_id SERIAL PRIMARY KEY,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price FLOAT NOT NULL CHECK (unit_price >= 0),
    line_total FLOAT NOT NULL CHECK (line_total >= 0),
    transaction_id INTEGER NOT NULL REFERENCES transaction(transaction_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES product(product_id) ON DELETE RESTRICT
);

-- Added to support order returns
CREATE TABLE IF NOT EXISTS transaction_return (
    return_id SERIAL PRIMARY KEY,
    return_date DATE NOT NULL DEFAULT CURRENT_DATE,
    quantity_returned INTEGER NOT NULL CHECK (quantity_returned > 0),
    refund_amount FLOAT NOT NULL CHECK (refund_amount >= 0),
    transaction_item_id INTEGER NOT NULL REFERENCES transaction_item(transaction_item_id) ON DELETE RESTRICT,
    customer_id INTEGER NOT NULL REFERENCES customer(customer_id) ON DELETE RESTRICT
    -- Note: Application logic or a trigger should validate that quantity_returned <= transaction_item.quantity
);

CREATE TABLE IF NOT EXISTS purchase_order (
    po_id SERIAL PRIMARY KEY,
    order_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Ordered', 'Received', 'Cancelled')),
    supplier_id INTEGER NOT NULL REFERENCES supplier(supplier_id) ON DELETE RESTRICT,
    store_id INTEGER NOT NULL REFERENCES store(store_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS purchase_order_item (
    po_item_id SERIAL PRIMARY KEY,
    quantity_ordered INTEGER NOT NULL CHECK (quantity_ordered > 0),
    unit_cost FLOAT NOT NULL CHECK (unit_cost >= 0),
    po_id INTEGER NOT NULL REFERENCES purchase_order(po_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES product(product_id) ON DELETE RESTRICT
);
