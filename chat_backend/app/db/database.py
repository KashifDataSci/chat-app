from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql:67234354Kashif@localhost/chat_db")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # Test connection before using it — drops stale connections
    pool_recycle=300,        # Recycle connections every 5 min (Railway closes idle after ~10 min)
    pool_size=5,             # Max persistent connections in pool
    max_overflow=10,         # Extra connections allowed under load
    connect_args={"connect_timeout": 10},  # Fail fast if DB is unreachable
)
session_local = sessionmaker(autoflush=False, autocommit=False, bind=engine)
base = declarative_base()

def get_db():
    db = session_local()
    try:
        yield db
    finally:
        db.close()