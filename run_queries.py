import csv
import config
from sqlalchemy import create_engine
from sqlalchemy import text

engine = create_engine(config.DATABASE_URL)

with engine.connect() as con:
    with open("queries.sql", "r", encoding="utf-8") as file:
        script_content = file.read()
        
    # Split the script by semicolons to handle multiple queries
    # and filter out empty strings/whitespace
    queries = [q.strip() for q in script_content.split(";") if q.strip()]
    
    for index, query_str in enumerate(queries, start=1):
        try:
            query = text(query_str)
            result = con.execute(query)
            
            # Check if the query returns rows (e.g., SELECT statements)
            if result.returns_rows:
                column_names = result.keys()
                rows = result.fetchall()
                
                output_file = f"output_result/query_result_{index}.csv"
                with open(output_file, "w", newline="", encoding="utf-8") as csv_file:
                    writer = csv.writer(csv_file)
                    
                    # Write header and rows
                    writer.writerow(column_names)
                    writer.writerows(rows)
                    
                print(f"Query {index} output saved to {output_file}")
            else:
                print(f"Query {index} executed successfully (no rows returned).")
                
        except Exception as e:
            print(f"Error executing Query {index}: {e}")
