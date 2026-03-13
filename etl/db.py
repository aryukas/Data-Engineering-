import os
import psycopg2
import sqlite3
from psycopg2.extras import execute_values
from logger import get_logger

logger = get_logger(__name__)

USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"
SQLITE_PATH = os.getenv("SQLITE_PATH", "market_data.db")

def get_db_connection():
    if USE_SQLITE:
        return sqlite3.connect(SQLITE_PATH)
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        port=os.getenv("DB_PORT", "5432")
    )

def insert_market_data(records):
    """Inserts processed records into the database (Postgres or SQLite)."""
    if not records:
        return
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        if USE_SQLITE:
            # SQLite ON CONFLICT syntax is slightly different but DO NOTHING works
            query = """
                INSERT OR IGNORE INTO market_data (instrument_id, price, volume, timestamp, vwap, is_outlier)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            values = [
                (r.instrument_id, r.price, r.volume, str(r.timestamp), r.vwap, r.is_outlier)
                for r in records
            ]
            cur.executemany(query, values)
        else:
            query = """
                INSERT INTO market_data (instrument_id, price, volume, timestamp, vwap, is_outlier)
                VALUES %s
                ON CONFLICT (instrument_id, timestamp) DO NOTHING
            """
            values = [
                (r.instrument_id, r.price, r.volume, r.timestamp, r.vwap, r.is_outlier)
                for r in records
            ]
            execute_values(cur, query, values)
            
        conn.commit()
        cur.close()
    except Exception as e:
        logger.error(f"Database insertion failed: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
