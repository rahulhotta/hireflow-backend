from pydantic import BaseModel, EmailStr, field_validator, model_validator
from uuid import UUID
from datetime import datetime



class PasswordMixin(BaseModel):
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

class UserCreate(PasswordMixin):
    full_name: str
    email: EmailStr


class UserResponse(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    is_active: bool
    created_at: datetime


class MessageResponse(BaseModel):
    status: str
    message: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(PasswordMixin):
    token: str

class ChangePassword(PasswordMixin):
    """Password (from PasswordMixin) is the new password"""
    current_password: str

    @model_validator(mode='after')
    def password_must_differ(self):
        if self.current_password == self.password:
            raise ValueError("new password must be different from the current password")
        return self

