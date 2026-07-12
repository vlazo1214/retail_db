# script to test db connection and generate csv's
import config

from faker import Faker
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import random

engine = create_engine(config.DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()
fake = Faker()

def populate_data():
    # 2. Populate Parents First
    # Example: Create 5 Suppliers
    suppliers = []
    for _ in range(5):
        s_query = text("INSERT INTO supplier (company_name, email, phone) VALUES (:name, :email, :phone) RETURNING supplier_id")
        result = session.execute(s_query, {"name": fake.company(), "email": fake.company_email(), "phone": fake.phone_number()})
        suppliers.append(result.fetchone()[0])
    
    # Example: Create 3 Stores
    stores = []
    for _ in range(3):
        st_query = text("INSERT INTO store (store_name, address, phone) VALUES (:name, :address, :phone) RETURNING store_id")
        result = session.execute(st_query, {"name": fake.company() + " Branch", "address": fake.address(), "phone": fake.phone_number()})
        stores.append(result.fetchone()[0])

    # 3. Populate Dependents
    # Example: Create 10 Products using a random supplier_id
    for _ in range(10):
        p_query = text("INSERT INTO product (product_name, category, unit_price, reorder_level, supplier_id) VALUES (:name, :cat, :price, :reorder, :sid)")
        session.execute(p_query, {
            "name": fake.word().capitalize() + " " + fake.word().capitalize(),
            "cat": fake.job(),
            "price": round(random.uniform(10.0, 500.0), 2),
            "reorder": str(random.randint(5, 50)),
            "sid": random.choice(suppliers)
        })

    session.commit()
    print("Data population complete!")

if __name__ == "__main__":
    populate_data()
