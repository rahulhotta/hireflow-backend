from datetime import  datetime, timedelta, timezone
import jwt
import secrets
import hashlib
from fastapi import Depends, HTTPException, status, Request
from app.database import get_db_connection
from psycopg2.extensions import connection
from app.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # Token valid for 24 hours
RESET_TOKEN_EXPIRE_MINUTES = 30
COOKIE_NAME = "access_token"



def generate_reset_token() -> str:
    """Creates the raw token that gets emailed to the user."""
    return secrets.token_urlsafe(32)

def hash_reset_token(token: str) -> str:
    """Hashes a reset token for safe storage/lookup in the DB."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def get_token_from_cookie(request: Request) -> str:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return token

def get_current_user(
        token: str = Depends(get_token_from_cookie),
        conn: connection = Depends(get_db_connection)):
    """
        1. Intercepts request and extracts JWT token from Cookie.
        2. Decodes token using SECRET_KEY and ALGORITHM.
        3. Fetches user from PostgreSQL using user ID ('sub') in the token payload.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except jwt.PyJWTError:
        raise credentials_exception

    cursor = conn.cursor()
    try:
        select_query = "select id, full_name, email, is_active, created_at from users where id = %s"
        cursor.execute(select_query, (user_id, ))
        user = cursor.fetchone()

        if user is None:
            raise credentials_exception
        return user
    except Exception as e:
        raise credentials_exception
    finally:
        cursor.close()


def create_access_token(data: dict) -> str:
    """
    Generates a signed JWT string containing payload claims and expiration date.
    """

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt