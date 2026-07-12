CREATE TABLE IF NOT EXISTS store (
    store_id SERIAL PRIMARY KEY,
    store_name VARCHAR(255),
    address VARCHAR(255),
    phone VARCHAR(20)
);

-- need constraints
CREATE TABLE IF NOT EXISTS employee (
    employee_id SERIAL PRIMARY KEY,
    employee_name VARCHAR(255),
    role VARCHAR(255),
    store_id INTEGER REFERENCES store(store_id)
);


CREATE TABLE IF NOT EXISTS customer (
    customer_id SERIAL PRIMARY KEY,
    customer_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(20)
);

-- differs from plan, 'contact_info' is too vague
CREATE TABLE IF NOT EXISTS supplier (
    supplier_id SERIAL PRIMARY KEY,
    company_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(20)
);

-- need constraints
CREATE TABLE IF NOT EXISTS product (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(255),
    category VARCHAR(255),
    unit_price FLOAT,
    reorder_level VARCHAR(255),
    supplier_id INTEGER REFERENCES supplier(supplier_id)
);

-- need constraints
CREATE TABLE IF NOT EXISTS inventory (
    inventory_id SERIAL PRIMARY KEY,
    quantity_on_hand INTEGER,
    last_updated DATE,
    store_id INTEGER REFERENCES store(store_id),
    product_id INTEGER REFERENCES product(product_id)
);

-- need constraints
CREATE TABLE IF NOT EXISTS sale (
    sale_id SERIAL PRIMARY KEY,
    sale_date DATE,
    total_amount FLOAT,
    store_id INTEGER REFERENCES store(store_id),
    employee_id INTEGER REFERENCES employee(employee_id),
    customer_id INTEGER REFERENCES customer(customer_id)
);

-- need constraints
CREATE TABLE IF NOT EXISTS sale_item (
    sale_item_id SERIAL PRIMARY KEY,
    -- not null?
    quantity INTEGER,
    unit_price FLOAT,
    line_total FLOAT,
    sale_id INTEGER REFERENCES sale(sale_id),
    product_id INTEGER REFERENCES product(product_id)
);

-- need constraints
CREATE TABLE IF NOT EXISTS purchase_order (
    po_id SERIAL PRIMARY KEY,
    order_date DATE,
    status VARCHAR(20),
    supplier_id INTEGER REFERENCES supplier(supplier_id),
    store_id INTEGER REFERENCES store(store_id)
);

-- need constraints
CREATE TABLE IF NOT EXISTS purchase_order_item (
    po_item_id SERIAL PRIMARY KEY,
    quantity_ordered INTEGER,
    unit_cost FLOAT,
    po_id INTEGER REFERENCES purchase_order(po_id),
    product_id INTEGER REFERENCES product(product_id)
);
