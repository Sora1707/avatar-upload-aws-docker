from fastapi import FastAPI, Depends, HTTPException, status
# Depends: dependency injection

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db import get_db

app = FastAPI(title="Avatar Profile API")

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
def register_test(payload: dict, db: Session = Depends(get_db)):
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

        # Insert user directly using SQL (matching our init.sql schema)
        # NOTE: In the real app later we will hash passwords, this is for network verification!
        insert_query = text(
            "INSERT INTO users (username, hashed_password) VALUES (:username, :password)"
        )
        db.execute(insert_query, {"username": username, "password": password})
        db.commit()
        
        return {"message": f"User {username} successfully registered via container network!"}
    except HTTPException as he:
        raise he
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))