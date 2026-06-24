import os
from datetime import datetime, timedelta, timezone
import jwt
import bcrypt

# Read secrets injected via Docker environments
SECRET_KEY = os.getenv("JWT_SECRET", "fallback-secret-for-local-dev")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def hash_password(password: str) -> str:
    """Converts a plain text password into a secure cryptographic string."""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_bytes.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compares a raw login input password against the saved DB hash matrix."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

def create_access_token(data: dict, expires_minutes: int = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
    """Generates a secure, cryptographically signed token that expires."""
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload.update({"exp": expire})
    
    # Sign the token using our secret signature key matrix
    encoded_jwt = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> dict:
    """Decodes a JWT token and returns its payload."""
    payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
    return payload