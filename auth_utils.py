from datetime import datetime, timedelta
from typing import Optional
import os

# Try to import auth libraries, handle if missing
try:
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
except ImportError:
    pwd_context = None

try:
    from jose import jwt, JWTError
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
    ALGORITHM = "HS256"
except ImportError:
    jwt = None

try:
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
except ImportError:
    id_token = None

def verify_password(plain_password, hashed_password):
    if not pwd_context:
        raise ImportError("passlib not installed")
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    if not pwd_context:
        raise ImportError("passlib not installed")
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    if not jwt:
        raise ImportError("python-jose not installed")
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_google_token(token: str, client_id: str = None):
    if not id_token:
        raise ImportError("google-auth not installed")
    try:
        # If client_id is None, it won't verify the audience (not recommended for prod)
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), client_id)
        return idinfo
    except ValueError:
        return None
