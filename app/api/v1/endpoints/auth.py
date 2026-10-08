from fastapi import APIRouter, Depends, status, Response
from psycopg2.extensions import connection
from fastapi.security import OAuth2PasswordRequestForm


from app.handlers.auth_handler import handle_login_user, handle_get_me
from app.database import get_db_connection

from app.schemas.user import UserCreate, UserResponse, MessageResponse
from app.handlers.auth_handler import handle_register_user
from app.core.security import get_current_user, COOKIE_NAME, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
        user_data: UserCreate,
        conn: connection = Depends(get_db_connection)):
    """
    HTTP Endpoint: Delegates registration logic to the auth handler.
    """
    return handle_register_user(user_data=user_data, conn=conn)


@router.post("/login", response_model=MessageResponse)
def login_user(
        response: Response,
        form_data: OAuth2PasswordRequestForm = Depends(),
        conn: connection = Depends(get_db_connection)):
    """
    HTTP Endpoint for User Login. Expects form-data (username & password).
    Sets the JWT in an HttpOnly cookie.
    """

    login_result =  handle_login_user(form_data=form_data, conn=conn)

    response.set_cookie(
        key=COOKIE_NAME,
        value=login_result['access_token'],
        httponly=True,
        secure=False,  # must be True in production (HTTPS)
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    return {
        "status": "success",
        "message": "Logged in successfully"
    }

@router.post("/logout", response_model=MessageResponse)
def logout(response: Response):
    """
    Clears the auth cookie. Works even if the token is missing or expired.
    """
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        secure=False,  # must match /login; True in production
        samesite="lax",
    )
    return {"status": "success", "message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user)):
    """
        Protected Endpoint: Returns current user details. Requires JWT in cookie.
    """
    return handle_get_me(current_user=current_user)