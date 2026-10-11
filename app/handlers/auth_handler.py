from fastapi import HTTPException, status
from datetime import datetime, timedelta, timezone
from psycopg2.extensions import connection
import bcrypt

from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import (
    create_access_token,
    generate_reset_token,
    hash_reset_token,
    RESET_TOKEN_EXPIRE_MINUTES,
)
from app.core.mailer import send_password_reset_email
from app.schemas.user import UserCreate, ForgotPasswordRequest, ResetPasswordRequest


user_table = "users"
password_reset_token_table = "password_reset_tokens"

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


def handle_forgot_password(payload: ForgotPasswordRequest, conn: connection) -> dict:
    """
    Issues a single-use password reset token and emails the link.

    Always returns the same generic response,whether or not the email
    exists, to prevent user enumeration.
    """

    generic_response = {
        "status": "success",
        "message": "If an account with that email exists, a reset link has been sent.",
    }

    cursor = conn.cursor()
    raw_token = None

    try:
        select_query = f"SELECT id, email FROM {user_table} WHERE email =%s;"
        cursor.execute(select_query, (payload.email,))

        user = cursor.fetchone()

        if user is None:
            return generic_response

        # Invalidate any outstanding tokens for this user.
        update_query = f"""
        UPDATE {password_reset_token_table} SET used = TRUE 
        WHERE user_id = %s AND used = FALSE;
        """
        cursor.execute(update_query, (user['id'],))
        raw_token = generate_reset_token()
        token_hash = hash_reset_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=RESET_TOKEN_EXPIRE_MINUTES
        )

        insert_reset_token_query = f"""
        INSERT INTO {password_reset_token_table} (user_id, token_hash, expires_at)
        VALUES (%s, %s, %s);
        """
        cursor.execute(insert_reset_token_query, (user["id"], token_hash, expires_at))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()

    if raw_token:
        send_password_reset_email(to_email=str(payload.email), raw_token=raw_token)
    return generic_response

def handle_reset_password(payload: ResetPasswordRequest, conn: connection) -> dict:
    """
    Consumes a single-use reset token and sets the new password.

    The token row and the user row are updated in ONE transaction so a
    token can never survive a successful password change.
    """
    invalid_token_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired reset token.",
    )

    token_hash = hash_reset_token(payload.token)
    cursor = conn.cursor()
    try:
        select_token_query = f"""
        SELECT id, user_id FROM {password_reset_token_table}       
        WHERE token_hash = %s AND used = FALSE AND expires_at > NOW(); 
        """
        cursor.execute(select_token_query, (token_hash,))
        token_row = cursor.fetchone()

        if token_row is None:
            raise invalid_token_exception

        new_hashed_password = hash_password(payload.password)

        update_user_query = f"""
        UPDATE {user_table} SET hashed_password = %s WHERE id = %s;
        """
        cursor.execute(update_user_query, (new_hashed_password, token_row["user_id"]))

        burn_token_query = f"""
        UPDATE {password_reset_token_table} SET used = TRUE WHERE id = %s;
        """
        cursor.execute(burn_token_query, (token_row["id"],))

        conn.commit()

        return {
            "status": "success",
            "message": "Password has been reset successfully.",
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()