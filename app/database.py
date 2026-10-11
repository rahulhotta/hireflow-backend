import psycopg2
from psycopg2.extras import RealDictCursor
from app.config import settings

def get_db_connection():
    """
    Creates and yields a raw PostgreSQL database connection using psycopg2.
    Uses RealDictCursor so returned database rows act like Python dictionaries
    (e.g., row['email'] instead of row[2]).
    """
    conn = psycopg2.connect(
        host=settings.DB_HOST,
        database=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASS,
        port=settings.DB_PORT,
        cursor_factory=RealDictCursor
    )
    try:
        yield conn
    finally:
        conn.close()