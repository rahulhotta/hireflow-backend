from pydantic import BaseModel, EmailStr, field_validator
from uuid import UUID
from datetime import datetime


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str

    @field_validator('password')
    @classmethod
    def validate_password_length(cls, v):
        """Ensure password is within bcrypt's 72-byte limit."""
        if len(v.encode('utf-8')) > 72:
            raise ValueError('password cannot be longer than 72 bytes')
        if len(v) < 8:
            raise ValueError('password must be at least 8 characters long')
        return v

class UserResponse(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    is_active: bool
    created_at: datetime
