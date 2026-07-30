# Publix Store Insights

A small Flask backend + themed frontend for running the reports in
`queries.sql` against the schema in `init.sql`.

## Option A: Docker Compose (recommended)

From the repo root (one level up from this folder):

```bash
cp .env.example .env      # then edit DB_USER / DB_PASSWORD / DB_PORT
docker compose up --build
```

This starts three containers:

| Service       | What it is                                  | URL                       |
|---------------|-----------------------------------------------|----------------------------|
| `db`          | Postgres 15, seeded from `init-db/init.sql`   | internal only (`db:5432`)  |
| `app`         | This Flask app                                | http://localhost:5000      |
| `db_explorer` | pgAdmin4                                      | http://localhost:8001      |

The `db` container runs everything in `./init-db/*.sql` automatically the
first time its volume is created, so the schema is ready before the app
starts (the app also waits on the db's healthcheck). The `app` container
talks to Postgres over the internal Docker network (`db:5432`), independent
of whatever host port `DB_PORT` maps to.

Run `import_data.py` to insert data into the database.

To reset everything (including the database volume):

```bash
docker compose down -v
```

## Option B: Run locally without Docker

### 1. Set up the database (PostgreSQL)

```bash
createdb publix
psql publix -f init.sql
# load your own sample data, then optionally:
psql publix -c "$(sed -n '/CREATE VIEW/,/;/p' queries.sql)"
```

The Flask app will also create the `supplier_product_summary` view itself
on startup if it's missing.

### 2. Install dependencies

```bash
cd publix_app
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure the connection

```bash
export DATABASE_URL=postgresql://user:password@localhost:5432/publix
```

(Or set `PGHOST` / `PGPORT` / `PGDATABASE` / `PGUSER` / `PGPASSWORD` individually.)

### 4. Run it

```bash
flask --app app run --debug
# or: python app.py
```

Visit http://localhost:5000 — pick a report from the "Aisle Guide" on the
left and it prints as a register receipt on the right.

## API reference

### Reports
| Endpoint                | Description                                   |
|-------------------------|------------------------------------------------|
| `GET /api/queries`       | List of available report keys + labels         |
| `GET /api/query/<key>`   | Run one report, returns `{columns, rows}`      |
| `GET /api/health`        | Simple DB connectivity check                   |

### CRUD (all 12 tables in init.sql)
| Endpoint                              | Description                                              |
|----------------------------------------|-----------------------------------------------------------|
| `GET /api/tables`                      | List of manageable tables + labels                        |
| `GET /api/tables/<table>/schema`       | Column metadata (types, required, FK dropdown options)    |
| `GET /api/tables/<table>`              | List all rows                                              |
| `POST /api/tables/<table>`             | Create a row (JSON body of column values)                  |
| `PUT /api/tables/<table>/<pk>`         | Update a row by primary key                                |
| `DELETE /api/tables/<table>/<pk>`      | Delete a row by primary key                                |

`<table>` is one of: `store`, `employee`, `employee_role_history`, `customer`,
`supplier`, `product`, `inventory`, `transaction`, `transaction_item`,
`transaction_return`, `purchase_order`, `purchase_order_item`.

The frontend's **Manage Data** tab is fully schema-driven — it calls
`/api/tables/<table>/schema` to build the form (text/number/date inputs,
dropdowns for foreign keys and the `purchase_order.status` enum) and the
listing table, so no per-table frontend code was needed. Foreign-key,
unique-constraint, and check-constraint violations from Postgres are caught
and turned into a plain-English error message shown in the UI rather than a
raw stack trace.

Report keys: `sales-by-store-monthly`, `sales-by-store-quarterly`,
`sales-by-store-yearly`, `top-products`, `top-customers`, `low-inventory`,
`supplier-performance`, `return-rate`, `returns-by-employee`,
`promoted-employees` — these map 1:1 to the queries in `queries.sql`.

## Files (this folder)

```
app.py                 Flask backend (routes + the SQL queries)
templates/index.html   Page shell
static/style.css       Publix-themed styling (receipt/register look)
static/script.js       Fetches queries and renders results
init.sql / queries.sql  Copied from the original brief, for reference
requirements.txt        Python dependencies
```

## Files (repo root)

```
docker-compose.yml      Postgres + pgAdmin + this app, wired together
.env.example            Copy to .env: DB_USER / DB_PASSWORD / DB_PORT
init-db/init.sql        Same schema, auto-run by Postgres on first boot
publix_app/             This app (Dockerfile lives here)
```
