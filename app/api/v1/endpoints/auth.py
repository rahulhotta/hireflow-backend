from fastapi import APIRouter, Depends, status
from psycopg2.extensions import connection

from app.database import get_db_connection

from app.schemas.user import UserCreate, UserResponse
from app.handlers.auth_handler import handle_register_user

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
        user_data: UserCreate,
        conn: connection = Depends(get_db_connection)):
    """
    HTTP Endpoint: Delegates registration logic to the auth handler.
    """
    return handle_register_user(user_data=user_data, conn=conn)