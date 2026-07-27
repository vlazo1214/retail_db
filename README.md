# Publix Store Insights

A small Flask backend + themed frontend for running the nine reports in
`queries.sql` against the schema in `init.sql`.

## 1. Set up the database (PostgreSQL)

```bash
createdb publix
psql publix -f init.sql
# load your own sample data, then optionally:
psql publix -c "$(sed -n '/CREATE VIEW/,/;/p' queries.sql)"
```

The Flask app will also create the `supplier_product_summary` view itself
on startup if it's missing.

## 2. Install dependencies

```bash
cd publix_app
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

## 3. Configure the connection

```bash
export DATABASE_URL=postgresql://user:password@localhost:5432/publix
```

(Or set `PGHOST` / `PGPORT` / `PGDATABASE` / `PGUSER` / `PGPASSWORD` individually.)

## 4. Run it

```bash
flask --app app run --debug
# or: python app.py
```

Visit http://localhost:5000 — pick a report from the "Aisle Guide" on the
left and it prints as a register receipt on the right.

## API reference

| Endpoint                | Description                                   |
|-------------------------|------------------------------------------------|
| `GET /api/queries`       | List of available report keys + labels         |
| `GET /api/query/<key>`   | Run one report, returns `{columns, rows}`      |
| `GET /api/health`        | Simple DB connectivity check                   |

Report keys: `sales-by-store-monthly`, `sales-by-store-quarterly`,
`sales-by-store-yearly`, `top-products`, `top-customers`, `low-inventory`,
`supplier-performance`, `return-rate`, `returns-by-employee`,
`promoted-employees` — these map 1:1 to the queries in `queries.sql`.

## Files

```
app.py                 Flask backend (routes + the 9 SQL queries)
templates/index.html   Page shell
static/style.css       Publix-themed styling (receipt/register look)
static/script.js       Fetches queries and renders results
init.sql / queries.sql  Copied from the original brief, for reference
requirements.txt        Python dependencies
```
