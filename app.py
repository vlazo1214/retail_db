"""
Publix Store Insights — Flask backend

Exposes the queries defined in queries.sql as a small JSON API and serves
the accompanying frontend.

Configuration (environment variables):
    DATABASE_URL   e.g. postgresql://user:password@localhost:5432/publix
    (falls back to the individual PG* vars below if DATABASE_URL isn't set)
    PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD

Run:
    pip install -r requirements.txt
    export DATABASE_URL=postgresql://user:password@localhost:5432/publix
    flask --app app run --debug
"""

import os
import logging
import config

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import psycopg2.errors
from psycopg2 import sql


app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("publix-app")

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URI")


def get_connection():
    """Open a new database connection using DATABASE_URL, or config.py's build of it."""
    return psycopg2.connect(DATABASE_URL or config.DATABASE_URL)


def run_query(sql: str):
    """Run a read-only query and return (columns, rows) as JSON-safe values."""
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description] if cur.description else []
            return columns, [dict(row) for row in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# The queries from queries.sql, kept verbatim so the API mirrors the
# analysis exactly. The supplier_product_summary VIEW (query 5) is created
# once at startup if it doesn't already exist.
# ---------------------------------------------------------------------------

QUERIES = {
    "sales-by-store-monthly": {
        "label": "Total sales by store: Monthly",
        "sql": """
            SELECT s.store_name,
                   DATE_TRUNC('month', t.transaction_date) AS month,
                   SUM(t.total_amount) AS total_sales
            FROM transaction t
            JOIN store s ON t.store_id = s.store_id
            GROUP BY s.store_name, DATE_TRUNC('month', t.transaction_date)
            ORDER BY s.store_name, month;
        """,
    },
    "sales-by-store-quarterly": {
        "label": "Total sales by store: Quarterly",
        "sql": """
            SELECT s.store_name,
                   DATE_TRUNC('quarter', t.transaction_date) AS quarter,
                   SUM(t.total_amount) AS total_sales
            FROM transaction t
            JOIN store s ON t.store_id = s.store_id
            GROUP BY s.store_name, DATE_TRUNC('quarter', t.transaction_date)
            ORDER BY s.store_name, quarter;
        """,
    },
    "sales-by-store-yearly": {
        "label": "Total sales by store: Yearly",
        "sql": """
            SELECT s.store_name,
                   DATE_TRUNC('year', t.transaction_date) AS year,
                   SUM(t.total_amount) AS total_sales
            FROM transaction t
            JOIN store s ON t.store_id = s.store_id
            GROUP BY s.store_name, DATE_TRUNC('year', t.transaction_date)
            ORDER BY s.store_name, year;
        """,
    },
    "top-products": {
        "label": "Top-selling products by quantity",
        "sql": """
            SELECT p.product_name, SUM(ti.quantity) AS total_sold
            FROM transaction_item ti
            JOIN product p ON ti.product_id = p.product_id
            GROUP BY p.product_name
            ORDER BY total_sold DESC
            LIMIT 5;
        """,
    },
    "top-customers": {
        "label": "Customers who spent above the average total",
        "sql": """
            SELECT customer_name
            FROM customer
            WHERE customer_id IN (
                SELECT customer_id
                FROM transaction
                GROUP BY customer_id
                HAVING SUM(total_amount) > (SELECT AVG(total_amount) FROM transaction)
            );
        """,
    },
    "low-inventory": {
        "label": "Products currently below reorder level at any store",
        "sql": """
            SELECT p.product_name, i.quantity_on_hand, p.reorder_level
            FROM inventory i
            JOIN product p ON i.product_id = p.product_id
            WHERE i.quantity_on_hand < p.reorder_level;
        """,
    },
    "supplier-performance": {
        "label": "Supplier product performance (view)",
        "sql": """
            SELECT * FROM supplier_product_summary ORDER BY total_units_sold DESC;
        """,
    },
    "return-rate": {
        "label": "Return rate by product",
        "sql": """
            SELECT p.product_name,
                   SUM(tr.refund_amount) AS total_refunded
            FROM transaction_return tr
            JOIN transaction_item ti ON tr.transaction_item_id = ti.transaction_item_id
            JOIN product p ON ti.product_id = p.product_id
            GROUP BY p.product_name
            ORDER BY total_refunded DESC;
        """,
    },
    "returns-by-employee": {
        "label": "Employees who processed the most returned transactions",
        "sql": """
            SELECT e.employee_name, s.store_name,
                   COUNT(tr.return_id) AS total_returns_processed
            FROM transaction_return tr
            JOIN transaction_item ti ON tr.transaction_item_id = ti.transaction_item_id
            JOIN transaction t ON ti.transaction_id = t.transaction_id
            JOIN employee e ON t.employee_id = e.employee_id
            JOIN store s ON e.store_id = s.store_id
            GROUP BY e.employee_name, s.store_name
            ORDER BY total_returns_processed DESC;
        """,
    },
    "promoted-employees": {
        "label": "Employees with a promotion history",
        "sql": """
            SELECT e.employee_name, s.store_name,
                   erh.previous_role, erh.new_role, erh.promotion_date
            FROM employee_role_history erh
            JOIN employee e ON erh.employee_id = e.employee_id
            JOIN store s ON e.store_id = s.store_id
            ORDER BY erh.promotion_date DESC;
        """,
    },
}

CREATE_VIEW_SQL = """
    CREATE OR REPLACE VIEW supplier_product_summary AS
    SELECT sup.company_name, p.product_name, SUM(ti.quantity) AS total_units_sold
    FROM transaction_item ti
    JOIN product p ON ti.product_id = p.product_id
    JOIN supplier sup ON p.supplier_id = sup.supplier_id
    GROUP BY sup.company_name, p.product_name;
"""


def ensure_view_exists():
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(CREATE_VIEW_SQL)
        conn.commit()
        conn.close()
    except Exception as exc:  # noqa: BLE001
        log.warning("Could not ensure supplier_product_summary view exists: %s", exc)


# ---------------------------------------------------------------------------
# Generic CRUD layer — one metadata entry per table in init.sql. The
# frontend uses /api/tables* to render forms/tables dynamically, so adding
# a table here is enough to get full CRUD without new frontend code.
#
# Column "type" drives how the frontend renders the field:
#   text   -> <input type="text">
#   int    -> <input type="number" step="1">
#   float  -> <input type="number" step="any">
#   date   -> <input type="date">
#   enum   -> <select> using "options"
#   fk     -> <select> populated from another table (see fk_table)
# ---------------------------------------------------------------------------

TABLES = {
    "store": {
        "label": "Stores",
        "pk": "store_id",
        "columns": [
            {"key": "store_name", "label": "Store Name", "type": "text", "required": True},
            {"key": "address", "label": "Address", "type": "text", "required": False},
            {"key": "phone", "label": "Phone", "type": "text", "required": False},
        ],
    },
    "employee": {
        "label": "Employees",
        "pk": "employee_id",
        "columns": [
            {"key": "employee_name", "label": "Employee Name", "type": "text", "required": True},
            {"key": "role", "label": "Role", "type": "text", "required": True},
            {"key": "store_id", "label": "Store", "type": "fk", "fk_table": "store", "required": True},
        ],
    },
    "employee_role_history": {
        "label": "Role History",
        "pk": "history_id",
        "columns": [
            {"key": "previous_role", "label": "Previous Role", "type": "text", "required": True},
            {"key": "new_role", "label": "New Role", "type": "text", "required": True},
            {"key": "promotion_date", "label": "Promotion Date", "type": "date", "required": False},
            {"key": "termination_date", "label": "Termination Date", "type": "date", "required": False},
            {"key": "employee_id", "label": "Employee", "type": "fk", "fk_table": "employee", "required": True},
        ],
    },
    "customer": {
        "label": "Customers",
        "pk": "customer_id",
        "columns": [
            {"key": "customer_name", "label": "Customer Name", "type": "text", "required": True},
            {"key": "email", "label": "Email", "type": "text", "required": False},
            {"key": "phone", "label": "Phone", "type": "text", "required": False},
        ],
    },
    "supplier": {
        "label": "Suppliers",
        "pk": "supplier_id",
        "columns": [
            {"key": "company_name", "label": "Company Name", "type": "text", "required": True},
            {"key": "email", "label": "Email", "type": "text", "required": False},
            {"key": "phone", "label": "Phone", "type": "text", "required": False},
        ],
    },
    "product": {
        "label": "Products",
        "pk": "product_id",
        "columns": [
            {"key": "product_name", "label": "Product Name", "type": "text", "required": True},
            {"key": "category", "label": "Category", "type": "text", "required": False},
            {"key": "unit_price", "label": "Unit Price", "type": "float", "required": True},
            {"key": "reorder_level", "label": "Reorder Level", "type": "int", "required": False},
            {"key": "supplier_id", "label": "Supplier", "type": "fk", "fk_table": "supplier", "required": True},
        ],
    },
    "inventory": {
        "label": "Inventory",
        "pk": "inventory_id",
        "columns": [
            {"key": "quantity_on_hand", "label": "Quantity On Hand", "type": "int", "required": False},
            {"key": "last_updated", "label": "Last Updated", "type": "date", "required": False},
            {"key": "store_id", "label": "Store", "type": "fk", "fk_table": "store", "required": True},
            {"key": "product_id", "label": "Product", "type": "fk", "fk_table": "product", "required": True},
        ],
    },
    "transaction": {
        "label": "Transactions",
        "pk": "transaction_id",
        "columns": [
            {"key": "transaction_date", "label": "Date", "type": "date", "required": False},
            {"key": "total_amount", "label": "Total Amount", "type": "float", "required": False},
            {"key": "store_id", "label": "Store", "type": "fk", "fk_table": "store", "required": True},
            {"key": "employee_id", "label": "Employee", "type": "fk", "fk_table": "employee", "required": True},
            {"key": "customer_id", "label": "Customer", "type": "fk", "fk_table": "customer", "required": False},
        ],
    },
    "transaction_item": {
        "label": "Transaction Items",
        "pk": "transaction_item_id",
        "columns": [
            {"key": "quantity", "label": "Quantity", "type": "int", "required": True},
            {"key": "unit_price", "label": "Unit Price", "type": "float", "required": True},
            {"key": "line_total", "label": "Line Total", "type": "float", "required": True},
            {"key": "transaction_id", "label": "Transaction", "type": "fk", "fk_table": "transaction", "required": True},
            {"key": "product_id", "label": "Product", "type": "fk", "fk_table": "product", "required": True},
        ],
    },
    "transaction_return": {
        "label": "Returns",
        "pk": "return_id",
        "columns": [
            {"key": "return_date", "label": "Return Date", "type": "date", "required": False},
            {"key": "quantity_returned", "label": "Quantity Returned", "type": "int", "required": True},
            {"key": "refund_amount", "label": "Refund Amount", "type": "float", "required": True},
            {"key": "transaction_item_id", "label": "Transaction Item", "type": "fk", "fk_table": "transaction_item", "required": True},
            {"key": "customer_id", "label": "Customer", "type": "fk", "fk_table": "customer", "required": True},
        ],
    },
    "purchase_order": {
        "label": "Purchase Orders",
        "pk": "po_id",
        "columns": [
            {"key": "order_date", "label": "Order Date", "type": "date", "required": False},
            {
                "key": "status",
                "label": "Status",
                "type": "enum",
                "options": ["Pending", "Ordered", "Received", "Cancelled"],
                "required": False,
            },
            {"key": "supplier_id", "label": "Supplier", "type": "fk", "fk_table": "supplier", "required": True},
            {"key": "store_id", "label": "Store", "type": "fk", "fk_table": "store", "required": True},
        ],
    },
    "purchase_order_item": {
        "label": "Purchase Order Items",
        "pk": "po_item_id",
        "columns": [
            {"key": "quantity_ordered", "label": "Quantity Ordered", "type": "int", "required": True},
            {"key": "unit_cost", "label": "Unit Cost", "type": "float", "required": True},
            {"key": "po_id", "label": "Purchase Order", "type": "fk", "fk_table": "purchase_order", "required": True},
            {"key": "product_id", "label": "Product", "type": "fk", "fk_table": "product", "required": True},
        ],
    },
}

# How to label each row when it's used as a foreign-key dropdown option.
# These are trusted, hardcoded SQL fragments (never built from request data).
FK_LABEL_EXPR = {
    "store": "store_name",
    "employee": "employee_name",
    "customer": "customer_name",
    "supplier": "company_name",
    "product": "product_name",
    "transaction": "'Txn #' || transaction_id || ' — ' || transaction_date",
    "transaction_item": "'Item #' || transaction_item_id",
    "purchase_order": "'PO #' || po_id || ' (' || status || ')'",
}


def describe_db_error(exc):
    """Turn common Postgres constraint errors into a friendlier message."""
    if isinstance(exc, psycopg2.errors.ForeignKeyViolation):
        return "That action conflicts with a related record (foreign key constraint)."
    if isinstance(exc, psycopg2.errors.UniqueViolation):
        return "A record with that value already exists (unique constraint)."
    if isinstance(exc, psycopg2.errors.NotNullViolation):
        return "A required field is missing."
    if isinstance(exc, psycopg2.errors.CheckViolation):
        return "One of the values doesn't meet the field's requirements (check constraint)."
    return str(exc)


def fetch_fk_options(fk_table):
    """Value/label pairs for populating a foreign-key <select>."""
    fk_meta = TABLES[fk_table]
    pk = fk_meta["pk"]
    label_expr = FK_LABEL_EXPR[fk_table]
    query = sql.SQL("SELECT {pk} AS value, {label} AS label FROM {tbl} ORDER BY {pk}").format(
        pk=sql.Identifier(pk),
        label=sql.SQL(label_expr),
        tbl=sql.Identifier(fk_table),
    )
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query)
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


@app.route("/api/tables")
def list_tables():
    """Metadata for building the 'Manage Data' table picker."""
    return jsonify([{"key": key, "label": meta["label"]} for key, meta in TABLES.items()])


@app.route("/api/tables/<table_key>/schema")
def table_schema(table_key):
    meta = TABLES.get(table_key)
    if not meta:
        return jsonify({"error": f"Unknown table '{table_key}'"}), 404

    columns = []
    for col in meta["columns"]:
        col_out = dict(col)
        if col["type"] == "fk":
            try:
                col_out["options"] = fetch_fk_options(col["fk_table"])
            except psycopg2.Error as exc:
                log.exception("Could not load FK options for %s", col["fk_table"])
                return jsonify({"error": describe_db_error(exc)}), 500
        columns.append(col_out)

    return jsonify({"key": table_key, "label": meta["label"], "pk": meta["pk"], "columns": columns})


@app.route("/api/tables/<table_key>", methods=["GET"])
def list_rows(table_key):
    meta = TABLES.get(table_key)
    if not meta:
        return jsonify({"error": f"Unknown table '{table_key}'"}), 404

    pk = meta["pk"]
    query = sql.SQL("SELECT * FROM {tbl} ORDER BY {pk}").format(
        tbl=sql.Identifier(table_key), pk=sql.Identifier(pk)
    )
    try:
        conn = get_connection()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query)
                rows = [dict(row) for row in cur.fetchall()]
        finally:
            conn.close()
    except psycopg2.Error as exc:
        log.exception("Database error listing '%s'", table_key)
        return jsonify({"error": describe_db_error(exc)}), 500

    return jsonify({"key": table_key, "pk": pk, "rows": rows})


@app.route("/api/tables/<table_key>", methods=["POST"])
def create_row(table_key):
    meta = TABLES.get(table_key)
    if not meta:
        return jsonify({"error": f"Unknown table '{table_key}'"}), 404

    body = request.get_json(silent=True) or {}
    allowed_keys = {c["key"] for c in meta["columns"]}
    required_keys = {c["key"] for c in meta["columns"] if c["required"]}

    missing = [k for k in required_keys if body.get(k) in (None, "")]
    if missing:
        return jsonify({"error": f"Missing required field(s): {', '.join(missing)}"}), 400

    insert_cols, insert_vals = [], []
    for key in allowed_keys:
        if key in body and body[key] not in (None, ""):
            insert_cols.append(key)
            insert_vals.append(body[key])

    if not insert_cols:
        return jsonify({"error": "No fields provided"}), 400

    query = sql.SQL("INSERT INTO {tbl} ({fields}) VALUES ({placeholders}) RETURNING *").format(
        tbl=sql.Identifier(table_key),
        fields=sql.SQL(", ").join(sql.Identifier(c) for c in insert_cols),
        placeholders=sql.SQL(", ").join(sql.Placeholder() * len(insert_cols)),
    )

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, insert_vals)
            new_row = dict(cur.fetchone())
        conn.commit()
    except psycopg2.Error as exc:
        conn.rollback()
        return jsonify({"error": describe_db_error(exc)}), 400
    finally:
        conn.close()

    return jsonify({"row": new_row}), 201


@app.route("/api/tables/<table_key>/<pk_value>", methods=["PUT"])
def update_row(table_key, pk_value):
    meta = TABLES.get(table_key)
    if not meta:
        return jsonify({"error": f"Unknown table '{table_key}'"}), 404

    pk = meta["pk"]
    body = request.get_json(silent=True) or {}
    allowed_keys = {c["key"] for c in meta["columns"]}
    update_cols = [k for k in body if k in allowed_keys]

    if not update_cols:
        return jsonify({"error": "No valid fields provided to update"}), 400

    set_clause = sql.SQL(", ").join(
        sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder()) for k in update_cols
    )
    values = [(body[k] if body[k] != "" else None) for k in update_cols]
    values.append(pk_value)

    query = sql.SQL("UPDATE {tbl} SET {set_clause} WHERE {pk} = {ph} RETURNING *").format(
        tbl=sql.Identifier(table_key), set_clause=set_clause, pk=sql.Identifier(pk), ph=sql.Placeholder()
    )

    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, values)
            updated = cur.fetchone()
            if not updated:
                conn.rollback()
                return jsonify({"error": f"No {table_key} row with {pk}={pk_value}"}), 404
            updated = dict(updated)
        conn.commit()
    except psycopg2.Error as exc:
        conn.rollback()
        return jsonify({"error": describe_db_error(exc)}), 400
    finally:
        conn.close()

    return jsonify({"row": updated})


@app.route("/api/tables/<table_key>/<pk_value>", methods=["DELETE"])
def delete_row(table_key, pk_value):
    meta = TABLES.get(table_key)
    if not meta:
        return jsonify({"error": f"Unknown table '{table_key}'"}), 404

    pk = meta["pk"]
    query = sql.SQL("DELETE FROM {tbl} WHERE {pk} = {ph} RETURNING {pk}").format(
        tbl=sql.Identifier(table_key), pk=sql.Identifier(pk), ph=sql.Placeholder()
    )

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, [pk_value])
            deleted = cur.fetchone()
            if not deleted:
                conn.rollback()
                return jsonify({"error": f"No {table_key} row with {pk}={pk_value}"}), 404
        conn.commit()
    except psycopg2.Error as exc:
        conn.rollback()
        return jsonify({"error": describe_db_error(exc)}), 400
    finally:
        conn.close()

    return jsonify({"deleted": pk_value})


@app.route("/")
def index():
    return render_template("index.html", queries=QUERIES)


@app.route("/api/queries")
def list_queries():
    """Metadata about the available queries, for building the frontend menu."""
    return jsonify(
        [{"key": key, "label": meta["label"]} for key, meta in QUERIES.items()]
    )


@app.route("/api/query/<key>")
def run_named_query(key):
    meta = QUERIES.get(key)
    if not meta:
        return jsonify({"error": f"Unknown query '{key}'"}), 404

    try:
        columns, rows = run_query(meta["sql"])
    except psycopg2.Error as exc:
        log.exception("Database error running query '%s'", key)
        return jsonify({"error": "Database error", "detail": str(exc)}), 500

    return jsonify({"key": key, "label": meta["label"], "columns": columns, "rows": rows})


@app.route("/api/health")
def health():
    try:
        conn = get_connection()
        conn.close()
        return jsonify({"status": "ok"})
    except Exception as exc:  # noqa: BLE001
        return jsonify({"status": "error", "detail": str(exc)}), 500


if __name__ == "__main__":
    ensure_view_exists()
    app.run(debug=True, use_reloader=False, host="0.0.0.0", port=5000)
