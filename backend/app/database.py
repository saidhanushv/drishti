from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# Format: mssql+pyodbc://username:password@server.database.windows.net/db_name?driver=ODBC+Driver+17+for+SQL+Server
SQLALCHEMY_DATABASE_URL = os.getenv("SQL_CONNECTION_STRING")

# Fallback for local testing if env var not set (using SQLite)
if not SQLALCHEMY_DATABASE_URL:
    SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
    print("WARNING: SQL_CONNECTION_STRING not found in .env, using local SQLite database.")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    # check_same_thread needed only for SQLite
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
