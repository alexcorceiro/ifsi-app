from pydantic import BaseModel, EmailStr,Field
from typing import Optional
from datetime import datetime


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    pseudo: Optional[str] = None
    phone_number: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    profile_picture_url: Optional[str] = None

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int 
    first_name: Optional[str]
    last_name: Optional[str]
    email: EmailStr
    pseudo: Optional[str]
    is_active: bool

class TokensOut(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None

class AuthOut(BaseModel):
    user: UserOut
    tokens: TokensOut


class MeOut(BaseModel):
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    pseudo: Optional[str] = None
    is_active: bool
    created_at: Optional[str] = None
