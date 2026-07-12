"""
generate_publix_data.py

Generates realistic fake data for a "Publix" grocery store chain database,
matching the schema defined in init.sql:

    store, employee, customer, supplier, product, inventory,
    sale, sale_item, purchase_order, purchase_order_item

Uses the Faker library for names, addresses, phone numbers, dates, etc.,
combined with hand-curated Publix-flavored reference data (store naming
convention, department/role names, grocery product categories) so the
output reads like a real regional supermarket chain rather than generic
placeholder data.

Output: a single .sql file of INSERT statements, written in FK-safe order,
plus a set of matching .csv files (one per table) for easy inspection or
bulk-loading with tools that prefer CSV.

Usage:
    python3 generate_publix_data.py
    python3 generate_publix_data.py --seed 42 --stores 8 --customers 500
"""

import argparse
import csv
import os
import random
from datetime import date, timedelta

from faker import Faker

# --------------------------------------------------------------------------
# Publix-flavored reference data
# --------------------------------------------------------------------------

FLORIDA_CITIES = [
    "Orlando", "Lakeland", "Tampa", "Winter Park", "Alafaya",
    "Kissimmee", "Gainesville", "Jacksonville", "Sarasota",
    "St. Petersburg", "Clearwater", "Winter Garden", "Ocoee",
    "Melbourne", "Daytona Beach", "Boca Raton", "West Palm Beach",
]

STORE_NAME_TEMPLATES = [
    "Publix Super Market at {plaza}",
    "Publix Super Market at {plaza} Shopping Center",
]

PLAZA_NAMES = [
    "Waterford Lakes", "Lake Nona", "Millenia", "East Colonial",
    "Alafaya Trail", "Winter Park Village", "The Villages",
    "Baldwin Park", "Hunter's Creek", "Dr. Phillips", "Conway Crossing",
    "University Square", "Oak Ridge", "Colonial Landing", "Metro West",
    "Southchase", "Avalon Park", "Sand Lake Commons",
]

EMPLOYEE_ROLES = [
    "Store Manager",
    "Assistant Store Manager",
    "Customer Service Manager",
    "Front Service Clerk",
    "Cashier",
    "Bagger",
    "Grocery Stock Clerk",
    "Produce Associate",
    "Deli Associate",
    "Bakery Associate",
    "Meat & Seafood Associate",
    "Pharmacist",
    "Pharmacy Technician",
    "Cake Decorator",
]

# category -> (typical unit price range, typical reorder level range)
PRODUCT_CATALOG = {
    "Produce": {
        "items": [
            "Bananas", "Gala Apples", "Roma Tomatoes", "Baby Carrots",
            "Russet Potatoes", "Yellow Onions", "Avocados", "Strawberries",
            "Blueberries", "Broccoli Crowns", "Iceberg Lettuce", "Limes",
        ],
        "price_range": (0.99, 6.99),
    },
    "Dairy": {
        "items": [
            "Publix Whole Milk Gallon", "Publix 2% Milk Half Gallon",
            "Large Grade A Eggs (Dozen)", "Publix Salted Butter",
            "Shredded Mozzarella Cheese", "Greek Yogurt (32oz)",
            "Heavy Whipping Cream", "American Cheese Slices",
        ],
        "price_range": (2.49, 7.99),
    },
    "Meat & Seafood": {
        "items": [
            "Boneless Chicken Breast", "80/20 Ground Beef",
            "Applewood Smoked Bacon", "Atlantic Salmon Fillet",
            "Publix Deli Rotisserie Chicken", "Pork Tenderloin",
            "Jumbo Shrimp (Peeled & Deveined)", "Italian Sausage Links",
        ],
        "price_range": (4.99, 15.99),
    },
    "Bakery": {
        "items": [
            "Publix Bakery French Bread", "Cuban Bread Loaf",
            "Chocolate Chip Cookies (12ct)", "Key Lime Pie",
            "Publix Deli Cuban Sandwich", "Dozen Glazed Donuts",
            "Sourdough Boule", "Birthday Cake, 8-inch Round",
        ],
        "price_range": (2.99, 24.99),
    },
    "Frozen": {
        "items": [
            "Frozen Mixed Vegetables", "Publix Vanilla Ice Cream",
            "Frozen Pepperoni Pizza", "Frozen Waffles",
            "Frozen Chicken Tenders", "Frozen Shrimp Bag",
            "Frozen Pie Crust (2ct)", "Frozen Orange Juice Concentrate",
        ],
        "price_range": (2.99, 9.99),
    },
    "Pantry": {
        "items": [
            "Publix Pasta, 16oz", "Marinara Sauce Jar", "Jasmine Rice, 2lb",
            "Extra Virgin Olive Oil", "Creamy Peanut Butter",
            "Canned Black Beans", "All-Purpose Flour, 5lb",
            "Granulated Sugar, 4lb", "Cereal, Family Size",
        ],
        "price_range": (1.49, 8.99),
    },
    "Beverages": {
        "items": [
            "Publix Orange Juice, 59oz", "Bottled Spring Water (24pk)",
            "Ground Coffee, 12oz", "Sweet Tea, Gallon",
            "Sparkling Water (8pk)", "Cola 12-pack Cans",
            "Publix Lemonade, 59oz",
        ],
        "price_range": (1.99, 12.99),
    },
    "Household": {
        "items": [
            "Paper Towels (6 Big Rolls)", "Bath Tissue (12 Mega Rolls)",
            "Laundry Detergent", "Dish Soap", "Trash Bags (30ct)",
            "All-Purpose Cleaner Spray", "Aluminum Foil, 75 sq ft",
        ],
        "price_range": (3.99, 19.99),
    },
    "Deli": {
        "items": [
            "Publix Deli Sliced Turkey Breast", "Provolone Cheese, Sliced",
            "Publix Chicken Tender Sub", "Potato Salad (Deli, 1lb)",
            "Publix Deli Ham, Sliced", "Macaroni Salad (Deli, 1lb)",
        ],
        "price_range": (3.99, 11.99),
    },
}

SUPPLIER_TYPES = [
    "Farms", "Foods", "Produce Distributors", "Foodservice", "Bakery Supply",
    "Meat Packing Co.", "Beverage Distributors", "Dairy Cooperative",
    "Wholesale Grocers", "Seafood Imports",
]

PO_STATUSES = ["Pending", "Shipped", "Received", "Cancelled"]

# --------------------------------------------------------------------------
# Data generation
# --------------------------------------------------------------------------


class PublixDataGenerator:
    def __init__(self, seed=None, num_stores=6, num_employees_per_store=(8, 15),
                 num_customers=300, num_suppliers=15, avg_products_per_category=6,
                 num_sales=1500, max_items_per_sale=6, num_purchase_orders=200,
                 max_items_per_po=8):
        self.fake = Faker()
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)

        self.num_stores = num_stores
        self.num_employees_per_store = num_employees_per_store
        self.num_customers = num_customers
        self.num_suppliers = num_suppliers
        self.avg_products_per_category = avg_products_per_category
        self.num_sales = num_sales
        self.max_items_per_sale = max_items_per_sale
        self.num_purchase_orders = num_purchase_orders
        self.max_items_per_po = max_items_per_po

        # storage for generated rows, keyed by table name
        self.data = {
            "store": [],
            "employee": [],
            "customer": [],
            "supplier": [],
            "product": [],
            "inventory": [],
            "sale": [],
            "sale_item": [],
            "purchase_order": [],
            "purchase_order_item": [],
        }

    # ---- individual table generators -----------------------------------

    def gen_stores(self):
        used_plazas = random.sample(PLAZA_NAMES, k=min(self.num_stores, len(PLAZA_NAMES)))
        for i in range(self.num_stores):
            plaza = used_plazas[i] if i < len(used_plazas) else self.fake.city() + " Plaza"
            name = random.choice(STORE_NAME_TEMPLATES).format(plaza=plaza)
            city = random.choice(FLORIDA_CITIES)
            self.data["store"].append({
                "store_id": i + 1,
                "store_name": name,
                "address": f"{self.fake.building_number()} {self.fake.street_name()}, {city}, FL {self.fake.zipcode_in_state(state_abbr='FL')}",
                "phone": self.fake.numerify("(###) ###-####"),
            })

    def gen_employees(self):
        emp_id = 1
        for store in self.data["store"]:
            n = random.randint(*self.num_employees_per_store)
            # ensure exactly one Store Manager per store
            roles = ["Store Manager"] + random.choices(
                [r for r in EMPLOYEE_ROLES if r != "Store Manager"], k=n - 1
            )
            for role in roles:
                self.data["employee"].append({
                    "employee_id": emp_id,
                    "employee_name": self.fake.name(),
                    "role": role,
                    "store_id": store["store_id"],
                })
                emp_id += 1

    def gen_customers(self):
        for i in range(self.num_customers):
            name = self.fake.name()
            self.data["customer"].append({
                "customer_id": i + 1,
                "customer_name": name,
                "email": self.fake.unique.email(),
                "phone": self.fake.numerify("(###) ###-####"),
            })

    def gen_suppliers(self):
        for i in range(self.num_suppliers):
            company = f"{self.fake.last_name()} {random.choice(SUPPLIER_TYPES)}"
            self.data["supplier"].append({
                "supplier_id": i + 1,
                "company_name": company,
                "email": self.fake.company_email(),
                "phone": self.fake.numerify("(###) ###-####"),
            })

    def gen_products(self):
        product_id = 1
        supplier_ids = [s["supplier_id"] for s in self.data["supplier"]]
        for category, info in PRODUCT_CATALOG.items():
            for item_name in info["items"]:
                low, high = info["price_range"]
                price = round(random.uniform(low, high), 2)
                self.data["product"].append({
                    "product_id": product_id,
                    "product_name": item_name,
                    "category": category,
                    "unit_price": price,
                    "reorder_level": str(random.choice([10, 15, 20, 25, 50, 100])),
                    "supplier_id": random.choice(supplier_ids),
                })
                product_id += 1

    def gen_inventory(self):
        inventory_id = 1
        today = date.today()
        for store in self.data["store"]:
            for product in self.data["product"]:
                # not every store necessarily stocks every product at full detail,
                # but for simplicity every store carries every product line
                self.data["inventory"].append({
                    "inventory_id": inventory_id,
                    "quantity_on_hand": random.randint(0, 250),
                    "last_updated": (today - timedelta(days=random.randint(0, 30))).isoformat(),
                    "store_id": store["store_id"],
                    "product_id": product["product_id"],
                })
                inventory_id += 1

    def gen_sales(self):
        sale_item_id = 1
        store_ids = [s["store_id"] for s in self.data["store"]]
        customer_ids = [c["customer_id"] for c in self.data["customer"]]
        employees_by_store = {}
        for e in self.data["employee"]:
            employees_by_store.setdefault(e["store_id"], []).append(e["employee_id"])

        today = date.today()
        for sale_id in range(1, self.num_sales + 1):
            store_id = random.choice(store_ids)
            employee_id = random.choice(employees_by_store[store_id])
            # ~85% of sales tied to a known (loyalty) customer, rest anonymous/cash sale
            customer_id = random.choice(customer_ids) if random.random() < 0.85 else None
            sale_date = today - timedelta(days=random.randint(0, 365))

            n_items = random.randint(1, self.max_items_per_sale)
            chosen_products = random.sample(self.data["product"], k=n_items)
            total_amount = 0.0

            for product in chosen_products:
                qty = random.randint(1, 5)
                unit_price = product["unit_price"]
                line_total = round(qty * unit_price, 2)
                total_amount += line_total
                self.data["sale_item"].append({
                    "sale_item_id": sale_item_id,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "line_total": line_total,
                    "sale_id": sale_id,
                    "product_id": product["product_id"],
                })
                sale_item_id += 1

            self.data["sale"].append({
                "sale_id": sale_id,
                "sale_date": sale_date.isoformat(),
                "total_amount": round(total_amount, 2),
                "store_id": store_id,
                "employee_id": employee_id,
                "customer_id": customer_id,
            })

    def gen_purchase_orders(self):
        po_item_id = 1
        store_ids = [s["store_id"] for s in self.data["store"]]
        supplier_ids = [s["supplier_id"] for s in self.data["supplier"]]
        today = date.today()

        for po_id in range(1, self.num_purchase_orders + 1):
            supplier_id = random.choice(supplier_ids)
            store_id = random.choice(store_ids)
            order_date = today - timedelta(days=random.randint(0, 180))
            status = random.choice(PO_STATUSES)

            self.data["purchase_order"].append({
                "po_id": po_id,
                "order_date": order_date.isoformat(),
                "status": status,
                "supplier_id": supplier_id,
                "store_id": store_id,
            })

            # only order products this supplier actually provides
            supplier_products = [p for p in self.data["product"] if p["supplier_id"] == supplier_id]
            if not supplier_products:
                continue
            n_items = min(len(supplier_products), random.randint(1, self.max_items_per_po))
            for product in random.sample(supplier_products, k=n_items):
                qty_ordered = random.randint(20, 300)
                unit_cost = round(product["unit_price"] * random.uniform(0.45, 0.75), 2)
                self.data["purchase_order_item"].append({
                    "po_item_id": po_item_id,
                    "quantity_ordered": qty_ordered,
                    "unit_cost": unit_cost,
                    "po_id": po_id,
                    "product_id": product["product_id"],
                })
                po_item_id += 1

    def generate_all(self):
        self.gen_stores()
        self.gen_employees()
        self.gen_customers()
        self.gen_suppliers()
        self.gen_products()
        self.gen_inventory()
        self.gen_sales()
        self.gen_purchase_orders()
        return self.data


# --------------------------------------------------------------------------
# Output helpers
# --------------------------------------------------------------------------

# order matters: respects FK dependencies from init.sql
TABLE_ORDER = [
    "store", "employee", "customer", "supplier", "product",
    "inventory", "sale", "sale_item", "purchase_order", "purchase_order_item",
]


def sql_literal(value):
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("'", "''")
    return f"'{escaped}'"


def write_sql(data, path):
    with open(path, "w") as f:
        f.write("-- Auto-generated fake data for Publix grocery store schema\n")
        f.write("-- Generated by generate_publix_data.py using Faker\n\n")
        for table in TABLE_ORDER:
            rows = data[table]
            if not rows:
                continue
            columns = list(rows[0].keys())
            f.write(f"-- {table} ({len(rows)} rows)\n")
            for row in rows:
                values = ", ".join(sql_literal(row[c]) for c in columns)
                f.write(
                    f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({values});\n"
                )
            f.write("\n")


def write_csvs(data, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for table in TABLE_ORDER:
        rows = data[table]
        if not rows:
            continue
        path = os.path.join(out_dir, f"{table}.csv")
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)


# --------------------------------------------------------------------------
# CLI entry point
# --------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Generate fake Publix grocery store data.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--stores", type=int, default=6, help="Number of store locations")
    parser.add_argument("--customers", type=int, default=300, help="Number of customers")
    parser.add_argument("--suppliers", type=int, default=15, help="Number of suppliers")
    parser.add_argument("--sales", type=int, default=1500, help="Number of sales transactions")
    parser.add_argument("--purchase-orders", type=int, default=200, help="Number of purchase orders")
    parser.add_argument("--out-dir", type=str, default=".", help="Output directory")
    args = parser.parse_args()

    generator = PublixDataGenerator(
        seed=args.seed,
        num_stores=args.stores,
        num_customers=args.customers,
        num_suppliers=args.suppliers,
        num_sales=args.sales,
        num_purchase_orders=args.purchase_orders,
    )
    data = generator.generate_all()

    os.makedirs(args.out_dir, exist_ok=True)
    sql_path = os.path.join(args.out_dir, "publix_fake_data.sql")
    csv_dir = os.path.join(args.out_dir, "publix_csv")

    write_sql(data, sql_path)
    write_csvs(data, csv_dir)

    print("Generated rows per table:")
    for table in TABLE_ORDER:
        print(f"  {table:22s} {len(data[table])}")
    print(f"\nSQL file:  {sql_path}")
    print(f"CSV files: {csv_dir}/*.csv")


if __name__ == "__main__":
    main()
