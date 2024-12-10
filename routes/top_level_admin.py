from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import HTMLResponse
from typing import Dict

from database import get_db
from models import User
from services.top_level_admin import TopLevelAdminService
from services.top_level_auth import check_top_level_admin
from dependencies import templates

router = APIRouter(prefix="/topadmin", tags=["top_level_admin"])

@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard_page(
    request: Request,
    current_user: User = Depends(check_top_level_admin),
    db: Session = Depends(get_db)
):
    """Render top level admin dashboard page"""
    try:
        print("Fetching dashboard data...")
        stats = TopLevelAdminService.get_dashboard_stats(db)
        print(f"Stats: {stats}")
        channels = TopLevelAdminService.get_all_channels(db)
        print(f"Channels: {channels}")
        
        return templates.TemplateResponse("top_level_admin_dashboard.html", {
            "request": request,
            "current_user": current_user,
            "stats": stats,
            "channels": channels,
            "locale": 'zh'
        })
    except Exception as e:
        print(f"Error rendering dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/channel/{channel_id}", response_class=HTMLResponse)
async def get_channel_details(
    request: Request,
    channel_id: int,
    current_user: User = Depends(check_top_level_admin),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific channel"""
    channel_details = TopLevelAdminService.get_channel_details(db, channel_id)
    return templates.TemplateResponse("admin_channel_details.html", {
        "request": request,
        "current_user": current_user,
        "channel": channel_details,
        "locale": 'zh'
    })

@router.get("/user/{user_id}/reports", response_class=HTMLResponse)
async def get_user_reports(
    request: Request,
    user_id: int,
    current_user: User = Depends(check_top_level_admin),
    db: Session = Depends(get_db)
):
    """Get all reports for a specific user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    reports = TopLevelAdminService.get_user_reports(db, user_id)
    return templates.TemplateResponse("admin_user_reports.html", {
        "request": request,
        "current_user": current_user,
        "user": user,
        "reports": reports,
        "locale": 'zh'
    })

@router.get("/report/{report_id}", response_class=HTMLResponse)
async def get_report_details(
    request: Request,
    report_id: int,
    current_user: User = Depends(check_top_level_admin),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific report"""
    report = TopLevelAdminService.get_report_details(db, report_id)
    return templates.TemplateResponse("admin_report_details.html", {
        "request": request,
        "current_user": current_user,
        "report": report,
        "locale": 'zh'
    })
