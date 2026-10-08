from fastapi import HTTPException, status
from psycopg2.extensions import connection
from passlib.context import CryptContext
import bcrypt

from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import create_access_token

from app.schemas.user import UserCreate

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )

def handle_register_user(user_data: UserCreate, conn: connection) -> dict:
    """
        Business logic for user registration:
        1. Checks if email is already registered.
        2. Hashes raw password.
        3. Inserts record into PostgreSQL using raw SQL.
        4. Commits transaction and returns created user dict.
    """
    cursor = conn.cursor()
    try:
        select_query = """
        SELECT id FROM users WHERE email = %s;
        """

        cursor.execute(select_query, (user_data.email,))
        existing_user = cursor.fetchone()

        if existing_user:
            raise HTTPException(
                status_code= status.HTTP_400_BAD_REQUEST,
                detail="A user with the email already exists"
            )

        # # Truncate password to 72 bytes (bcrypt limit) if necessary
        # password_bytes = user_data.password.encode('utf-8')
        # if len(password_bytes) > 72:
        #     password = password_bytes[:72].decode('utf-8', errors='ignore')
        # else:
        #     password = user_data.password
        hashed_password = hash_password(user_data.password)

        insert_query = """
            INSERT INTO users (full_name, email, hashed_password)
            VALUES (%s, %s, %s)
            RETURNING id, full_name, email, is_active, created_at;
        """
        cursor.execute(insert_query, (user_data.full_name, user_data.email, hashed_password) )
        new_user = cursor.fetchone()

        conn.commit()
        return new_user

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()


def handle_login_user(form_data: OAuth2PasswordRequestForm, conn: connection) -> dict:

    cursor = conn.cursor()

    try:
        # 1. Query PostgreSQL for the user by email
        select_user_query = "select id, email, hashed_password from users where email = %s"
        cursor.execute(select_user_query, (form_data.username,))
        user = cursor.fetchone()


        # 2. Check if the user exists and the password is correct
        if not user or not verify_password(form_data.password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 3. Generate signed JWT access token containing user's UUID
        access_token = create_access_token(data={"sub": str(user["id"])})

        # 4. Return the token according to OAuth2 specification
        return {"access_token": access_token}
    finally:
        cursor.close()


def handle_get_me(current_user: dict) -> dict:
    """Returns profile data for authenticated user."""
    return current_user