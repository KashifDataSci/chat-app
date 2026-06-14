from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import OperationalError
import os
import time
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql:67234354Kashif@localhost/chat_db")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # Test connection before using — drops stale connections
    pool_recycle=300,        # Recycle connections every 5 min (Railway idles at ~10 min)
    pool_size=5,
    max_overflow=10,
    connect_args={"connect_timeout": 10},
)
session_local = sessionmaker(autoflush=False, autocommit=False, bind=engine)
base = declarative_base()


def get_db():
    """
    Yield a DB session with retry logic.
    Railway's free-tier DB can take a few seconds to wake from sleep,
    so we retry up to 3 times before giving up.
    """
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds between retries

    for attempt in range(1, MAX_RETRIES + 1):
        db = session_local()
        try:
            # Force a lightweight connection test
            db.execute(__import__('sqlalchemy').text("SELECT 1"))
            yield db
            return
        except OperationalError as e:
            db.close()
            if attempt < MAX_RETRIES:
                print(f"[DB] Connection attempt {attempt} failed — retrying in {RETRY_DELAY}s... ({e.__class__.__name__})")
                time.sleep(RETRY_DELAY)
            else:
                print(f"[DB] All {MAX_RETRIES} connection attempts failed.")
                raise
        finally:
            db.close()