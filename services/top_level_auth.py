from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
import models

async def check_top_level_admin(request: Request, db: Session = Depends(get_db)):
    """Middleware to check if user is top level admin"""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or not user.is_top_level_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    return user

def verify_top_level_admin_role(user: models.User) -> bool:
    """Verify if a user has top level admin role"""
    return user.is_top_level_admin and user.role == "top_level_admin"

def get_top_level_admin_permissions():
    """Get the list of permissions for top level admin"""
    return {
        "can_view_all_channels": True,
        "can_view_all_reports": True,
        "can_view_all_users": True,
        "can_manage_channels": True,
        "can_manage_users": True
    }
