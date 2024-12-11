from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Dict, Any

from dependencies import get_db, get_current_user, templates
from services import second_level_user
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/second-level/dashboard", response_class=HTMLResponse)
async def second_level_dashboard_page(request: Request):
    """Serve the second level user dashboard page"""
    return templates.TemplateResponse(
        "second_level_dashboard.html",
        {"request": request}
    )

@router.get("/api/second-level/dashboard", response_model=Dict[str, Any])
async def get_second_level_dashboard(
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user)
):
    """Get dashboard data for second level user"""
    try:
        if current_user["role"] != "level_2":
            raise HTTPException(
                status_code=403,
                detail="Only second level users can access this endpoint"
            )
        
        dashboard_data = await second_level_user.get_dashboard_data(
            db=db,
            user_id=current_user["user_id"]
        )
        return dashboard_data
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
