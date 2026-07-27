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

from flask import Flask, jsonify, render_template
from flask_cors import CORS
import psycopg2
import psycopg2.extras


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
        "label": "Total sales by store — Monthly",
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
        "label": "Total sales by store — Quarterly",
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
        "label": "Total sales by store — Yearly",
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
