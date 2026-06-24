import os
import time
# Connection Manager
from sqlalchemy import create_engine
# Session
from sqlalchemy.orm import sessionmaker

# 1. Grab environment variables loaded by Docker env_file
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_NAME = os.getenv("POSTGRES_DB", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_HOST = "database" 

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 2. Create the Database Engine
# We add a retry loop because sometimes Postgres takes a split second to accept connections 
# even after its internal health check reports as green.
for attempt in range(5):
    try:
        engine = create_engine(DATABASE_URL, echo=True) # echo for SQL commands debugging
        SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
        # Test connection
        with engine.connect() as conn:
            print("Successfully connected to the database container!")
            break
    except Exception as e:
        print(f"Database connection attempt {attempt + 1} failed. Retrying in 2s...")
        time.sleep(2)
else:
    raise Exception("Could not connect to the database container.")

# Dependency to inject DB sessions into FastAPI endpoints
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()