import psycopg2
from psycopg2.extras import RealDictCursor

#database credentials
DB_HOST = "127.0.0.1"
DB_NAME = "hireflow_db"
DB_USER = "postgres"
DB_PASS = "LordVoldemort@2002"  # Replace with your local Postgres password
DB_PORT = 5434

def get_db_connection():
    """
    Creates and yields a raw PostgreSQL database connection using psycopg2.
    Uses RealDictCursor so returned database rows act like Python dictionaries
    (e.g., row['email'] instead of row[2]).
    """
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        port=DB_PORT,
        cursor_factory=RealDictCursor
    )
    try:
        yield conn
    finally:
        conn.close()