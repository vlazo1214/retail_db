# script to establish db connection and import csv's
import os
import psycopg2

# Table order respects foreign key constraints (parents before children)
TABLE_ORDER = [
    "store", 
    "employee", 
    "employee_role_history", 
    "customer", 
    "supplier",
    "product", 
    "inventory", 
    "transaction", 
    "transaction_item",
    "transaction_return", 
    "purchase_order", 
    "purchase_order_item",
]

def import_csv_to_postgres():
    # Database connection parameters (matches your docker-compose settings)
    db_params = {
        "dbname": "retail_db",
        "user": "admin",
        "password": "password",
        "host": "localhost",
        "port": 5432
    }

    csv_dir = "csv_data"

    print("Connecting to the database...")
    try:
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        # Temporarily disable triggers/foreign key checks if needed, 
        # though inserting in TABLE_ORDER prevents FK violations.
        cursor.execute("SET session_replication_role = 'replica';")

        for table in TABLE_ORDER:
            csv_path = os.path.join(csv_dir, f"{table}.csv")
            
            if not os.path.exists(csv_path):
                print(f"Skipping {table}: {csv_path} not found.")
                continue

            print(f"Importing data into table: {table}...")
            
            with open(csv_path, "r", encoding="utf-8") as f:
                # Read the header to know column names
                header = f.readline().strip()
                columns = header.split(",")
                
                # Construct the PostgreSQL COPY command
                sql_copy = f"COPY {table} ({', '.join(columns)}) FROM STDIN WITH CSV HEADER;"
                
                cursor.copy_expert(sql=sql_copy, file=f)

        # Re-enable replication role / constraints
        cursor.execute("SET session_replication_role = 'origin';")
        
        conn.commit()
        print("\nAll CSV data successfully imported into the database!")

    except Exception as e:
        if 'conn' in locals() and conn:
            conn.rollback()
        print(f"An error occurred during import: {e}")
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    import_csv_to_postgres()
