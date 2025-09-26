from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import hashlib

SECRET_KEY = "dgfdszegezsegezge"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120
REFRESH_SECRET_KEY = "hethtrehtrzsgr"

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    minutes: Optional[int] = None
) -> str:
    """
    Génère un access token.
    Priorité : expires_delta > minutes > ACCESS_TOKEN_EXPIRE_MINUTES.
    """
    to_encode = data.copy()

    if expires_delta is not None:
        expire = datetime.now(timezone.utc) + expires_delta
    elif minutes is not None:
        expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_access_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

def create_refresh_token(data: Dict, days: int = 15) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=days)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
