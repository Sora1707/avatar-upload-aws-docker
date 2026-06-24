from fastapi import FastAPI, Depends, HTTPException, status
# Depends: dependency injection
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from sqlalchemy.orm import Session
from sqlalchemy import text

import uuid
import jwt

from app.db import get_db
from app.auth import hash_password, verify_password, create_access_token, decode_token
from app.s3 import generate_upload_url, generate_download_url

""" ---------------------- API CONTEXT ---------------------- """

app = FastAPI(title="Avatar Profile API")

security_scheme = HTTPBearer()

""" ---------------------- ROUTING ---------------------- """

@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    try:
        # Perform a quick query to verify container-to-container database connection
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"API is live but Database is unreachable: {str(e)}"
        )

@app.post("/api/register", status_code=status.HTTP_201_CREATED)
def register(payload: dict, db: Session = Depends(get_db)):
    username = payload.get("username")
    password = payload.get("password")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
        
    try:
        # Check if user already exists
        check_query = text("SELECT username FROM users WHERE username = :username")
        existing_user = db.execute(check_query, {"username": username}).fetchone()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken")

        hashed_password = hash_password(password)

        # Insert user directly using SQL (matching our init.sql schema)
        insert_query = text(
            "INSERT INTO users (username, hashed_password) VALUES (:username, :hashed_password)"
        )
        db.execute(insert_query, {"username": username, "hashed_password": hashed_password})
        db.commit()
        
        return {"message": f"User {username} successfully registered via container network!"}
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/api/login")
def login(payload: dict, db: Session = Depends(get_db)):
    username = payload.get("username")
    password = payload.get("password")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")
        
    # Look up the user record
    query = text("SELECT username, hashed_password FROM users WHERE username = :username")
    user = db.execute(query, {"username": username}).fetchone()

    if not user: 
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User {username} not found"
        )

    # If user doesn't exist, or the cryptographically matched hash fails, trigger an error
    correct_password = verify_password(password, user.hashed_password)
    if not user or not correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Incorrect username or password"
        )
        
    # Generate the JWT token payload containing their non-sensitive identity metadata
    access_token = create_access_token(data={"sub": user.username})
    
    return {
        "access_token": access_token, 
        "token_type": "bearer"
    }

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):
    """Acts as a router gatekeeper. Decodes and verifies incoming JWT bearer badges."""
    token = credentials.credentials
    try:
        # Decode signature using our system's container environment key matrix
        payload = decode_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token identity metadata")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please log in again.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

@app.get("/api/me")
def get_profile(
    current_user: str = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Only reachable if a client supplies a valid, active JWT bearer handshake payload."""
    
    query = text("SELECT username, avatar_s3_key FROM users WHERE username = :username")
    user = db.execute(query, {"username": current_user}).fetchone()

    avatar_download_url = None
    
    # If the user has an avatar uploaded, generate a secure temporary link for the frontend to render
    if user and user.avatar_s3_key:
        avatar_download_url = generate_download_url(user.avatar_s3_key, expires_in=900)
    
    return {
        "authenticated": True,
        "username": current_user,
        "role": "user",
        "avatar_url": avatar_download_url,
        "message": f"Welcome back {current_user}! Your container connection is completely secure."
    }

@app.get("/api/avatar/upload-url")
def get_avatar_upload_url(current_user: str = Depends(get_current_user)):
    """Generates a unique S3 object key and a temporary direct-upload URL for the authenticated user."""
    
    # Create a completely unique filename using a UUID to prevent filename collisions in S3
    unique_id = uuid.uuid4().hex
    object_key = f"avatars/{current_user}_{unique_id}.png"

    print(f"Generated object key: {object_key}")
    
    # Generate the direct-to-S3 PUT url (valid for 5 minutes)
    upload_url = generate_upload_url(object_key=object_key, expires_in=300)
    
    return {
        "upload_url": upload_url,
        "object_key": object_key,
        "message": "Use this upload_url via a PUT request, then call /api/avatar/confirm to save the key."
    }

@app.post("/api/avatar/confirm")
def confirm_avatar_upload(payload: dict, current_user: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """Updates the user's database record with the S3 object key after a successful browser upload."""
    object_key = payload.get("object_key")
    if not object_key:
        raise HTTPException(status_code=400, detail="Missing object_key")
        
    try:
        # Save the S3 object reference key to the user row
        update_query = text("UPDATE users SET avatar_s3_key = :avatar_s3_key WHERE username = :username")
        db.execute(update_query, {"avatar_s3_key": object_key, "username": current_user})
        db.commit()
        return {"status": "success", "message": "Profile avatar updated successfully!"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))