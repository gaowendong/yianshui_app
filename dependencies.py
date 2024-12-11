from fastapi.templating import Jinja2Templates
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from sqlalchemy.orm import Session
from database import SessionLocal
from utils.auth_utils import verify_access_token

# Configure Jinja2 Templates with absolute path
template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
templates = Jinja2Templates(directory=template_path)

# Security scheme for JWT token
security = HTTPBearer()

def get_db():
    """Database dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> dict:
    """Get current authenticated user"""
    try:
        token = credentials.credentials
        payload = verify_access_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token"
            )
            
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=str(e)
        )
