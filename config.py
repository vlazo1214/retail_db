import os
from dotenv import load_dotenv

load_dotenv()

# DB variables
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
# Default "localhost" for running outside Docker; inside docker-compose this
# should be set to the service name (e.g. DB_HOST=db) since the app and db
# are separate containers and don't share a network "localhost".
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = "retail_db"
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
