from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Replace with your actual RDS credentials
DB_USERNAME = "admin"
DB_PASSWORD = "Admin123admin123"
DB_HOST = "wearables-app-db.cpoyy4oa2oky.us-east-2.rds.amazonaws.com"
DB_PORT = "3306"  # for MySQL
DB_NAME = "wearables_app_db" # Initial database name; different from wearables-app-db (instance)

# Example for MySQL (adjust if using PostgreSQL)
DATABASE_URL = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

