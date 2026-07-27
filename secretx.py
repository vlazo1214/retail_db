"""
Generates realistic fake data for a supermarket database,
matching the updated schema defined in init.sql:

    store, employee, employee_role_history, customer, supplier, product, 
    inventory, transaction, transaction_item, transaction_return, 
    purchase_order, purchase_order_item

Output: a single .sql file of INSERT statements written in FK-safe order,
plus matching .csv files per table.
"""

import argparse
import csv
import os
import random
from datetime import date, timedelta

from faker import Faker

# --------------------------------------------------------------------------
# Reference data
# --------------------------------------------------------------------------

FLORIDA_CITIES = [
    "Orlando", "Lakeland", "Tampa", "Winter Park", "Alafaya",
    "Kissimmee", "Gainesville", "Jacksonville", "Sarasota",
    "St. Petersburg", "Clearwater", "Winter Garden", "Ocoee",
    "Melbourne", "Daytona Beach", "Boca Raton", "West Palm Beach",
]

STORE_NAME_TEMPLATES = [
    "Secretx at {plaza}",
    "Secretx at {plaza} Shopping Center",
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

PRODUCT_CATALOG = {
    "Produce": [
        "Bananas", "Gala Apples", "Roma Tomatoes", "Baby Carrots",
        "Russet Potatoes", "Yellow Onions", "Avocados", "Strawberries",
        "Blueberries", "Broccoli Crowns", "Iceberg Lettuce", "Limes",
    ],
    "Dairy": [
        "Whole Milk Gallon", "2% Milk Half Gallon",
        "Large Grade A Eggs (Dozen)", "Salted Butter",
        "Shredded Mozzarella Cheese", "Greek Yogurt (32oz)",
        "Heavy Whipping Cream", "American Cheese Slices",
    ],
    "Meat & Seafood": [
        "Boneless Chicken Breast", "80/20 Ground Beef",
        "Applewood Smoked Bacon", "Atlantic Salmon Fillet",
        "Rotisserie Chicken", "Pork Tenderloin",
        "Jumbo Shrimp", "Italian Sausage Links",
    ],
    "Bakery": [
        "French Bread", "Cuban Bread Loaf",
        "Chocolate Chip Cookies (12ct)", "Key Lime Pie",
        "Cuban Sandwich", "Dozen Glazed Donuts",
        "Sourdough Boule", "Birthday Cake",
    ],
    "Frozen": [
        "Frozen Mixed Vegetables", "Vanilla Ice Cream",
        "Frozen Pepperoni Pizza", "Frozen Waffles",
        "Frozen Chicken Tenders", "Frozen Shrimp Bag",
    ],
    "Pantry": [
        "Pasta 16oz", "Marinara Sauce Jar", "Jasmine Rice 2lb",
        "Extra Virgin Olive Oil", "Creamy Peanut Butter",
        "Canned Black Beans", "All-Purpose Flour 5lb",
    ],
    "Beverages": [
        "Orange Juice 59oz", "Bottled Spring Water (24pk)",
        "Ground Coffee 12oz", "Sweet Tea Gallon",
        "Sparkling Water (8pk)", "Cola 12-pack Cans",
    ],
    "Household": [
        "Paper Towels (6 Rolls)", "Bath Tissue (12 Rolls)",
        "Laundry Detergent", "Dish Soap", "Trash Bags (30ct)",
    ],
}

SUPPLIER_TYPES = [
    "Farms", "Foods", "Produce Distributors", "Foodservice", "Bakery Supply",
    "Meat Packing Co.", "Beverage Distributors", "Dairy Cooperative",
    "Wholesale Grocers", "Seafood Imports",
]

PO_STATUSES = ["Pending", "Ordered", "Received", "Cancelled"]

# --------------------------------------------------------------------------
# Data Generator
# --------------------------------------------------------------------------


class DatabaseDataGenerator:
    def __init__(
        self,
        seed=42,
        num_stores=10,
        num_employees=100,
        num_customers=200,
        num_suppliers=20,
        num_transactions=500,
        num_purchase_orders=100,
        num_returns=100,
        num_promotions=100,
    ):
        self.fake = Faker()
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)

        self.num_stores = num_stores
        self.num_employees = num_employees
        self.num_customers = num_customers
        self.num_suppliers = num_suppliers
        self.num_transactions = num_transactions
        self.num_purchase_orders = num_purchase_orders
        self.num_returns = num_returns
        self.num_promotions = num_promotions

        self.data = {
            "store": [],
            "employee": [],
            "employee_role_history": [],
            "customer": [],
            "supplier": [],
            "product": [],
            "inventory": [],
            "transaction": [],
            "transaction_item": [],
            "transaction_return": [],
            "purchase_order": [],
            "purchase_order_item": [],
        }

    def gen_stores(self):
        for i in range(1, self.num_stores + 1):
            plaza = random.choice(PLAZA_NAMES)
            name = random.choice(STORE_NAME_TEMPLATES).format(plaza=plaza)
            city = random.choice(FLORIDA_CITIES)
            self.data["store"].append({
                "store_id": i,
                "store_name": name,
                "address": f"{self.fake.building_number()} {self.fake.street_name()}, {city}, FL {self.fake.zipcode_in_state(state_abbr='FL')}",
                "phone": self.fake.numerify("(###) ###-####"),
            })

    def gen_employees(self):
        store_ids = [s["store_id"] for s in self.data["store"]]
        for i in range(1, self.num_employees + 1):
            self.data["employee"].append({
                "employee_id": i,
                "employee_name": self.fake.name(),
                "role": random.choice(EMPLOYEE_ROLES),
                "store_id": random.choice(store_ids),
            })

    def gen_employee_role_history(self):
        today = date.today()
        emp_ids = [e["employee_id"] for e in self.data["employee"]]
        for i in range(1, self.num_promotions + 1):
            promo_date = today - timedelta(days=random.randint(30, 730))
            term_date = promo_date + timedelta(days=random.randint(180, 365))
            self.data["employee_role_history"].append({
                "history_id": i,
                "previous_role": random.choice(EMPLOYEE_ROLES),
                "new_role": random.choice(EMPLOYEE_ROLES),
                "promotion_date": promo_date.isoformat(),
                "termination_date": term_date.isoformat(),
                "employee_id": random.choice(emp_ids),
            })

    def gen_customers(self):
        for i in range(1, self.num_customers + 1):
            self.data["customer"].append({
                "customer_id": i,
                "customer_name": self.fake.name(),
                "email": self.fake.unique.email(),
                "phone": self.fake.numerify("(###) ###-####"),
            })

    def gen_suppliers(self):
        for i in range(1, self.num_suppliers + 1):
            company = f"{self.fake.last_name()} {random.choice(SUPPLIER_TYPES)}"
            self.data["supplier"].append({
                "supplier_id": i,
                "company_name": company,
                "email": self.fake.company_email(),
                "phone": self.fake.numerify("(###) ###-####"),
            })

    def gen_products(self):
        product_id = 1
        supplier_ids = [s["supplier_id"] for s in self.data["supplier"]]
        for category, items in PRODUCT_CATALOG.items():
            for item in items:
                self.data["product"].append({
                    "product_id": product_id,
                    "product_name": item,
                    "category": category,
                    "unit_price": round(random.uniform(1.50, 25.00), 2),
                    "reorder_level": random.choice([10, 15, 20, 25, 50]),
                    "supplier_id": random.choice(supplier_ids),
                })
                product_id += 1

    def gen_inventory(self):
        inventory_id = 1
        today = date.today()
        # Generates inventory entries for store-product pairs
        for store in self.data["store"]:
            # Sample subset of products to keep table count reasonable
            sampled_products = random.sample(self.data["product"], k=min(10, len(self.data["product"])))
            for product in sampled_products:
                self.data["inventory"].append({
                    "inventory_id": inventory_id,
                    "quantity_on_hand": random.randint(5, 150),
                    "last_updated": (today - timedelta(days=random.randint(0, 15))).isoformat(),
                    "store_id": store["store_id"],
                    "product_id": product["product_id"],
                })
                inventory_id += 1

    def gen_transactions(self):
        item_id = 1
        store_ids = [s["store_id"] for s in self.data["store"]]
        customer_ids = [c["customer_id"] for c in self.data["customer"]]
        emp_ids = [e["employee_id"] for e in self.data["employee"]]
        today = date.today()

        for tx_id in range(1, self.num_transactions + 1):
            tx_date = today - timedelta(days=random.randint(0, 180))
            
            # Create 1 to 3 items per transaction
            n_items = random.randint(25, 50)
            chosen_products = random.sample(self.data["product"], k=n_items)
            total_amount = 0.0

            for product in chosen_products:
                qty = random.randint(1, 4)
                price = product["unit_price"]
                line_total = round(qty * price, 2)
                total_amount += line_total

                self.data["transaction_item"].append({
                    "transaction_item_id": item_id,
                    "quantity": qty,
                    "unit_price": price,
                    "line_total": line_total,
                    "transaction_id": tx_id,
                    "product_id": product["product_id"],
                })
                item_id += 1

            self.data["transaction"].append({
                "transaction_id": tx_id,
                "transaction_date": tx_date.isoformat(),
                "total_amount": round(total_amount, 2),
                "store_id": random.choice(store_ids),
                "employee_id": random.choice(emp_ids),
                "customer_id": random.choice(customer_ids) if random.random() < 0.85 else None,
            })

    def gen_transaction_returns(self):
        tx_items = self.data["transaction_item"]
        customer_ids = [c["customer_id"] for c in self.data["customer"]]
        today = date.today()
        
        sampled_items = random.choices(tx_items, k=self.num_returns)
        for i, item in enumerate(sampled_items, start=1):
            qty_returned = random.randint(1, item["quantity"])
            refund = round(qty_returned * item["unit_price"], 2)
            
            self.data["transaction_return"].append({
                "return_id": i,
                "return_date": (today - timedelta(days=random.randint(0, 30))).isoformat(),
                "quantity_returned": qty_returned,
                "refund_amount": refund,
                "transaction_item_id": item["transaction_item_id"],
                "customer_id": random.choice(customer_ids),
            })

    def gen_purchase_orders(self):
        po_item_id = 1
        store_ids = [s["store_id"] for s in self.data["store"]]
        supplier_ids = [s["supplier_id"] for s in self.data["supplier"]]
        today = date.today()

        for po_id in range(1, self.num_purchase_orders + 1):
            supplier_id = random.choice(supplier_ids)
            po_date = today - timedelta(days=random.randint(0, 90))

            self.data["purchase_order"].append({
                "po_id": po_id,
                "order_date": po_date.isoformat(),
                "status": random.choice(PO_STATUSES),
                "supplier_id": supplier_id,
                "store_id": random.choice(store_ids),
            })

            supplier_products = [p for p in self.data["product"] if p["supplier_id"] == supplier_id]
            if not supplier_products:
                supplier_products = random.sample(self.data["product"], k=1)

            chosen = random.sample(supplier_products, k=min(len(supplier_products), random.randint(1, 2)))
            for product in chosen:
                qty = random.randint(20, 100)
                cost = round(product["unit_price"] * 0.6, 2)
                self.data["purchase_order_item"].append({
                    "po_item_id": po_item_id,
                    "quantity_ordered": qty,
                    "unit_cost": cost,
                    "po_id": po_id,
                    "product_id": product["product_id"],
                })
                po_item_id += 1

    def generate_all(self):
        self.gen_stores()
        self.gen_employees()
        self.gen_employee_role_history()
        self.gen_customers()
        self.gen_suppliers()
        self.gen_products()
        self.gen_inventory()
        self.gen_transactions()
        self.gen_transaction_returns()
        self.gen_purchase_orders()
        return self.data


# --------------------------------------------------------------------------
# File Formatting & Output
# --------------------------------------------------------------------------

TABLE_ORDER = [
    "store", "employee", "employee_role_history", "customer", "supplier",
    "product", "inventory", "transaction", "transaction_item",
    "transaction_return", "purchase_order", "purchase_order_item",
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
        f.write("-- Generated mock SQL data\n\n")
        for table in TABLE_ORDER:
            rows = data[table]
            if not rows:
                continue
            columns = list(rows[0].keys())
            f.write(f"-- {table} ({len(rows)} rows)\n")
            for row in rows:
                values = ", ".join(sql_literal(row[c]) for c in columns)
                f.write(f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({values});\n")
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


def main():
    parser = argparse.ArgumentParser(description="Generate fake retail database data.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--stores", type=int, default=10, help="Number of stores")
    parser.add_argument("--employees", type=int, default=100, help="Number of employees")
    parser.add_argument("--customers", type=int, default=100, help="Number of customers")
    parser.add_argument("--suppliers", type=int, default=20, help="Number of suppliers")
    parser.add_argument("--transactions", type=int, default=100, help="Number of transactions")
    parser.add_argument("--purchase-orders", type=int, default=100, help="Number of purchase orders")
    parser.add_argument("--returns", type=int, default=100, help="Number of returns")
    parser.add_argument("--promotions", type=int, default=100, help="Number of promotion history records")
    parser.add_argument("--out-dir", type=str, default=".", help="Output folder")
    args = parser.parse_args()

    generator = DatabaseDataGenerator(
        seed=args.seed,
        num_stores=args.stores,
        num_employees=args.employees,
        num_customers=args.customers,
        num_suppliers=args.suppliers,
        num_transactions=args.transactions,
        num_purchase_orders=args.purchase_orders,
        num_returns=args.returns,
        num_promotions=args.promotions,
    )
    data = generator.generate_all()

    os.makedirs(args.out_dir, exist_ok=True)
    sql_path = os.path.join(args.out_dir, "fake_data.sql")
    csv_dir = os.path.join(args.out_dir, "csv_data")

    write_sql(data, sql_path)
    write_csvs(data, csv_dir)

    print("Generated rows per table:")
    for table in TABLE_ORDER:
        print(f"  {table:24s} {len(data[table])}")
    print(f"\nSQL output:  {sql_path}")
    print(f"CSV output:  {csv_dir}/*.csv")


if __name__ == "__main__":
    main()
