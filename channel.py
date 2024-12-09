from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from services import channel as channel_service
from services.auth import get_current_user
from models import User
from typing import Optional
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
import os

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/channel/dashboard", response_class=HTMLResponse)
async def channel_dashboard(request: Request):
    return templates.TemplateResponse("channel_dashboard.html", {"request": request})

@router.get("/channel/user/{user_id}/reports", response_class=HTMLResponse)
async def level2_user_reports(request: Request, user_id: int):
    return templates.TemplateResponse("level2_user_reports.html", {"request": request})

@router.get("/api/channel/dashboard")
async def get_channel_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.channel_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with any channel"
        )

    dashboard_data = channel_service.get_channel_dashboard_data(db, current_user.channel_id)
    if not dashboard_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    return dashboard_data

@router.get("/api/channel/{channel_id}/user/{user_id}/reports")
async def get_level2_user_reports_with_auth(
    channel_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        print(f"Fetching reports for user {user_id} in channel {channel_id}")
        print(f"Current user: ID={current_user.id}, Channel={current_user.channel_id}, Role={current_user.role}")

        # Check if the current user has access to this channel
        if not current_user.channel_id or current_user.channel_id != channel_id:
            print("Access denied: User not authorized for this channel")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this channel's data"
            )

        # Get the level2 user
        level2_user = db.query(User).filter(User.id == user_id).first()
        if not level2_user:
            print(f"User {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        print(f"Found level2 user: ID={level2_user.id}, Channel={level2_user.channel_id}, Role={level2_user.role}")

        # Check if the user belongs to the specified channel
        if level2_user.channel_id != channel_id:
            print(f"User {user_id} does not belong to channel {channel_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not belong to this channel"
            )

        # Check if the user is a level 2 user
        if level2_user.role != "level_2":
            print(f"User {user_id} is not a level 2 user")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not a level 2 user"
            )

        # Get the user's reports data
        reports_data = channel_service.get_level2_user_reports_data(db, user_id)
        if not reports_data:
            print(f"No reports found for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reports data not found"
            )

        print(f"Found {len(reports_data['reports'])} reports for user {user_id}")
        return reports_data

    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/api/channel/user/{user_id}/reports")
async def get_level2_user_reports(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check if the current user has access to this level2 user's reports
    if not current_user.channel_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with any channel"
        )

    # Get the level2 user
    level2_user = db.query(User).filter(User.id == user_id).first()
    if not level2_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if the level2 user belongs to the same channel as the current user
    if level2_user.channel_id != current_user.channel_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user's reports"
        )

    # Get the user's reports data
    reports_data = channel_service.get_level2_user_reports_data(db, user_id)
    if not reports_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reports data not found"
        )

    return reports_data

@router.post("/api/channel/deposit")
async def deposit_funds(
    amount: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.channel_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with any channel"
        )

    if amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be greater than 0"
        )

    updated_channel = channel_service.update_channel_balance(
        db, current_user.channel_id, amount
    )
    if not updated_channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found"
        )

    return {"new_balance": updated_channel.balance}
